#!/usr/bin/env python3
"""Download the Federal Reserve SCF codebooks and summary extracts."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zipfile import is_zipfile

BASE_URL = "https://www.federalreserve.gov/econres/"
SURVEY_YEARS = (1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025)
USER_AGENT = "Mozilla/5.0 (compatible; SCFResearchScript/1.0)"


class LinkParser(HTMLParser):
    """Collect link text and destinations from an SCF page."""

    def __init__(self) -> None:
        super().__init__()
        self.current: tuple[str | None, list[str]] | None = None
        self.links: list[tuple[str | None, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.current = (dict(attrs).get("href"), [])

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current[1].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current is not None:
            href, parts = self.current
            self.links.append((href, " ".join("".join(parts).split())))
            self.current = None


def read_url(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read()


def survey_page(year: int) -> str:
    name = "scfindex.htm" if year == 2025 else f"scf_{year}.htm"
    return urljoin(BASE_URL, name)


def find_source_links(year: int) -> tuple[str, str]:
    page_url = survey_page(year)
    parser = LinkParser()
    parser.feed(read_url(page_url).decode("utf-8", errors="replace"))
    links = [(urljoin(page_url, href), label) for href, label in parser.links if href]
    summary = next(
        (url for url, label in links
         if urlparse(url).path.lower().endswith(f"scfp{year}s.zip")
         and "stata extract" in label.lower()),
        None,
    )
    codebook = next(
        (url for url, label in links
         if "codebook" in label.lower()
         and urlparse(url).path.lower().endswith((".txt", ".ascii"))),
        None,
    )
    missing = [name for name, url in (("Stata summary extract", summary), ("codebook", codebook)) if url is None]
    if missing:
        raise RuntimeError(f"Could not find {', '.join(missing)} on {page_url}")
    return summary, codebook


def download(url: str, destination: Path, *, force: bool = False) -> None:
    if destination.exists() and not force:
        if destination.suffix.lower() != ".zip" or is_zipfile(destination):
            print(f"Already present: {destination}")
            return
        destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if destination.suffix.lower() == ".zip" and not is_zipfile(temporary):
            raise RuntimeError(f"Downloaded file is not a valid ZIP: {url}")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    print(f"Downloaded: {destination} ({destination.stat().st_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--years", nargs="+", type=int, choices=SURVEY_YEARS,
        default=SURVEY_YEARS, help="SCF survey waves to download (default: 1989–2025).",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent / "data",
        help="Directory for downloaded files (default: ./data).",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing files.")
    args = parser.parse_args()

    raw_dir = args.output_dir / "raw"
    docs_dir = args.output_dir / "documentation"
    for year in args.years:
        page_url = survey_page(year)
        summary, codebook = find_source_links(year)
        print(f"{year}: {page_url}")
        download(summary, raw_dir / f"scfp_{year}_stata.zip", force=args.force)
        download(codebook, docs_dir / f"codebook_{year}.txt", force=args.force)

    print(f"\nVerified SCF waves: {', '.join(map(str, args.years))}")
    print(f"Summary extracts: {raw_dir}")
    print(f"Codebooks: {docs_dir}")


if __name__ == "__main__":
    main()
