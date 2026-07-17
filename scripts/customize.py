import argparse
import re
from pathlib import Path

from scripts.website_source import crawl_website, normalize_website_url, write_review_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a review bundle from a university website source of truth."
    )
    parser.add_argument("--institution")
    parser.add_argument("--website")
    parser.add_argument("--support-destination")
    parser.add_argument("--max-pages", type=int, default=25)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--output", type=Path, default=Path("data/imported"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    institution = args.institution or input("University name: ").strip()
    website_input = args.website or input("University website (HTTPS source of truth): ").strip()
    support = args.support_destination or input(
        "Human support destination [Student Services Center]: "
    ).strip()
    if not institution:
        raise ValueError("University name is required.")
    website = normalize_website_url(website_input)
    support = support or "Student Services Center"
    destination = args.output / _slug(institution)

    print(f"Crawling up to {args.max_pages} approved-by-robots pages from {website}...")
    pages = crawl_website(
        website,
        max_pages=args.max_pages,
        max_depth=args.max_depth,
    )
    manifest = write_review_bundle(
        pages,
        destination,
        institution_name=institution,
        website=website,
    )
    _write_env(institution, website, support)

    print(f"Created {len(pages)} reviewable pages in {destination}.")
    print(f"Review {manifest} and remove anything not approved for student-facing answers.")
    print(f"Then index it with: python scripts/ingest.py --source {destination}")


def _write_env(institution: str, website: str, support: str) -> None:
    env_path = Path(".env")
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else "APP_MODE=mock\n"
    values = {
        "INSTITUTION_NAME": institution,
        "UNIVERSITY_WEBSITE": website,
        "SUPPORT_DESTINATION": support,
    }
    lines = existing.splitlines()
    for key, value in values.items():
        replacement = f"{key}={value}"
        index = next((i for i, line in enumerate(lines) if line.startswith(f"{key}=")), None)
        if index is None:
            lines.append(replacement)
        else:
            lines[index] = replacement
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "university"


if __name__ == "__main__":
    main()
