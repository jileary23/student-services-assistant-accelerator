from pathlib import Path

import pytest

from scripts.ingest import load_documents
from scripts.website_source import crawl_website, normalize_website_url, write_review_bundle


def test_normalize_website_url_requires_public_https_hostname() -> None:
    assert normalize_website_url("www.jmu.edu/index.shtml") == (
        "https://www.jmu.edu/index.shtml"
    )
    with pytest.raises(ValueError, match="HTTPS"):
        normalize_website_url("http://www.jmu.edu")
    with pytest.raises(ValueError, match="public hostname"):
        normalize_website_url("https://127.0.0.1")


def test_crawl_stays_on_host_and_obeys_robots() -> None:
    responses = {
        "https://www.jmu.edu/robots.txt": (
            "text/plain",
            "User-agent: *\nDisallow: /private/\n",
        ),
        "https://www.jmu.edu/index.shtml": (
            "text/html",
            """
            <html><head><title>James Madison University</title></head><body>
            <nav>Navigation should not be indexed.</nav>
            <main>Official student services information with enough useful text for review.
            This page explains registration, financial aid, housing, and student support.</main>
            <a href="/student-life.shtml">Student life</a>
            <a href="/private/records.shtml">Private</a>
            <a href="https://example.com/outside.html">Outside</a>
            </body></html>
            """,
        ),
        "https://www.jmu.edu/student-life.shtml": (
            "text/html",
            """
            <html><head><title>Student Life</title></head><body><main>
            Student life services include housing and campus support information for
            current and prospective students. Contact the responsible office for decisions.
            </main></body></html>
            """,
        ),
    }
    fetched: list[str] = []

    def fetcher(url: str) -> tuple[str, str, str]:
        fetched.append(url)
        content_type, body = responses[url]
        return url, content_type, body

    pages = crawl_website(
        "https://www.jmu.edu/index.shtml",
        max_pages=10,
        max_depth=2,
        delay_seconds=0,
        fetcher=fetcher,
    )

    assert [page.title for page in pages] == ["James Madison University", "Student Life"]
    assert "Navigation should not be indexed" not in pages[0].content
    assert "https://www.jmu.edu/private/records.shtml" not in fetched
    assert all("example.com" not in url for url in fetched)


def test_write_review_bundle_preserves_sources(tmp_path: Path) -> None:
    pages = crawl_website(
        "https://www.jmu.edu/index.shtml",
        max_pages=1,
        delay_seconds=0,
        fetcher=lambda url: (
            url,
            "text/plain" if url.endswith("robots.txt") else "text/html",
            "User-agent: *\nAllow: /\n"
            if url.endswith("robots.txt")
            else "<title>JMU</title><main>" + "Approved student information. " * 8 + "</main>",
        ),
    )
    manifest = write_review_bundle(
        pages,
        tmp_path,
        institution_name="James Madison University",
        website="https://www.jmu.edu/index.shtml",
    )

    assert manifest.exists()
    assert "review_status" in manifest.read_text(encoding="utf-8")
    markdown = next(tmp_path.glob("*.md")).read_text(encoding="utf-8")
    assert "Source: https://www.jmu.edu/index.shtml" in markdown
    assert load_documents(tmp_path)[0]["source_url"] == "https://www.jmu.edu/index.shtml"
