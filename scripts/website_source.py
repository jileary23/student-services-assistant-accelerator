from __future__ import annotations

import ipaddress
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

USER_AGENT = "StudentServicesAccelerator/1.0 (+institution content review)"
_SKIP_TAGS = {"script", "style", "nav", "header", "footer", "form", "svg", "noscript"}
_HTML_SUFFIXES = {"", ".htm", ".html", ".shtml"}


class Fetcher(Protocol):
    def __call__(self, url: str) -> tuple[str, str, str]: ...


@dataclass(frozen=True)
class ImportedPage:
    id: str
    title: str
    source_url: str
    content: str


class _ContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "a" and self._skip_depth == 0:
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        if self._skip_depth == 0 and not self._in_title:
            self.text_parts.append(text)


def normalize_website_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme != "https":
        raise ValueError("The university website must use HTTPS.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Enter a public university website without credentials.")
    _reject_ip_address(parsed.hostname)
    path = parsed.path or "/"
    return parsed._replace(path=path, fragment="").geturl()


def crawl_website(
    website: str,
    *,
    max_pages: int = 25,
    max_depth: int = 2,
    delay_seconds: float = 0.25,
    fetcher: Fetcher | None = None,
) -> list[ImportedPage]:
    if not 1 <= max_pages <= 200:
        raise ValueError("max_pages must be between 1 and 200.")
    if not 0 <= max_depth <= 5:
        raise ValueError("max_depth must be between 0 and 5.")

    start_url = normalize_website_url(website)
    host = urlparse(start_url).hostname
    if host is None:
        raise ValueError("The university website must include a hostname.")
    active_fetcher = fetcher or fetch_url
    robots = _load_robots(start_url, active_fetcher)
    queue: deque[tuple[str, int]] = deque([(start_url, 0)])
    queued = {start_url}
    visited: set[str] = set()
    pages: list[ImportedPage] = []

    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        if url in visited or not robots.can_fetch(USER_AGENT, url):
            continue
        visited.add(url)
        final_url, content_type, html = active_fetcher(url)
        final_url = _canonicalize_url(final_url)
        if not _is_allowed_page(final_url, host) or "text/html" not in content_type.lower():
            continue

        parser = _ContentParser()
        parser.feed(html)
        content = " ".join(parser.text_parts)
        if len(content) < 120:
            continue
        title = " ".join(parser.title_parts).strip() or urlparse(final_url).path
        page_id = _page_id(final_url)
        pages.append(
            ImportedPage(
                id=page_id,
                title=title[:200],
                source_url=final_url,
                content=content,
            )
        )

        if depth < max_depth:
            for href in parser.links:
                linked_url = _canonicalize_url(urljoin(final_url, href))
                if linked_url not in queued and _is_allowed_page(linked_url, host):
                    queued.add(linked_url)
                    queue.append((linked_url, depth + 1))
        if delay_seconds:
            time.sleep(delay_seconds)

    if not pages:
        raise ValueError("No reviewable HTML pages were found at the university website.")
    return pages


def write_review_bundle(
    pages: list[ImportedPage],
    destination: Path,
    *,
    institution_name: str,
    website: str,
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for page in pages:
        markdown = f"# {page.title}\n\nSource: {page.source_url}\n\n{page.content}\n"
        (destination / f"{page.id}.md").write_text(markdown, encoding="utf-8")

    manifest = {
        "institution_name": institution_name,
        "website": normalize_website_url(website),
        "review_status": "pending",
        "instructions": "Review every page and remove unapproved content before indexing.",
        "pages": [asdict(page) | {"content": f"{page.id}.md"} for page in pages],
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def fetch_url(url: str) -> tuple[str, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - URL is validated by caller
        final_url = normalize_website_url(response.geturl())
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read(2_000_000).decode(charset, errors="replace")
        return final_url, content_type, body


def _load_robots(website: str, fetcher: Fetcher) -> RobotFileParser:
    parsed = urlparse(website)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots = RobotFileParser(robots_url)
    try:
        _, content_type, body = fetcher(robots_url)
        if "text/plain" in content_type.lower():
            robots.parse(body.splitlines())
        else:
            robots.parse([])
    except (OSError, ValueError):
        robots.parse([])
    return robots


def _canonicalize_url(url: str) -> str:
    clean_url, _ = urldefrag(url)
    parsed = urlparse(clean_url)
    return parsed._replace(query="").geturl()


def _is_allowed_page(url: str, host: str) -> bool:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    return (
        parsed.scheme == "https"
        and parsed.hostname == host
        and not parsed.username
        and not parsed.password
        and suffix in _HTML_SUFFIXES
    )


def _reject_ip_address(host: str) -> None:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError("The university website must be a public hostname.")
    raise ValueError("Use the university hostname rather than a direct IP address.")


def _page_id(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.hostname}-{parsed.path.strip('/') or 'home'}"
    return re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")[:100]
