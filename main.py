"""
main.py – Entry point for the news scraper.

Usage:
    python main.py                        # run with default config.json
    python main.py --config my_config.json
    python main.py --source "tagesschau – Landwirtschaft"  # single source
    python main.py --dry-run              # discover URLs only, don't save
"""

import argparse
import json
import logging
import sys
from tqdm import tqdm

from scraper.fetcher import ArticleFetcher
from scraper.parser import ArticleParser
from scraper.database import ArticleDatabase


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        level=level,
    )


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(config: dict, source_filter: str | None, dry_run: bool) -> None:
    settings = config["scraper_settings"]
    keywords = config["keywords"]
    sources = config["sources"]

    if source_filter:
        sources = [s for s in sources if s["name"] == source_filter]
        if not sources:
            logging.error("No source found with name: %s", source_filter)
            sys.exit(1)

    fetcher = ArticleFetcher(settings)
    parser = ArticleParser(settings, keywords)
    db = ArticleDatabase(config["database"])

    total_saved = 0
    total_skipped = 0

    for source in sources:
        print(f"\n>>> {source['name']}")
        urls = fetcher.get_article_urls(source)

        if not urls:
            print("    No URLs found.")
            continue

        print(f"    {len(urls)} URLs discovered")

        if dry_run:
            for url in urls:
                print(f"    [dry-run] {url}")
            continue

        for url in tqdm(urls, desc="    Parsing", unit="art", leave=False):
            article = parser.parse(url, source["name"])
            if article is None:
                total_skipped += 1
                continue
            saved = db.save(article)
            if saved:
                total_saved += 1
            else:
                total_skipped += 1

    if not dry_run:
        stats = db.stats()
        print(f"\n{'='*50}")
        print(f"  Run complete")
        print(f"  Newly saved : {total_saved}")
        print(f"  Skipped     : {total_skipped} (no keyword match or duplicate)")
        print(f"  DB total    : {stats['total']} articles")
        print(f"\n  By source:")
        for src, count in stats["by_source"].items():
            print(f"    {src}: {count}")
        print(f"{'='*50}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Keyword-based news scraper")
    parser.add_argument("--config", default="config.json", help="Path to config file")
    parser.add_argument("--source", default=None, help="Run only this source (by name)")
    parser.add_argument("--dry-run", action="store_true", help="Discover URLs only, don't fetch or save")
    parser.add_argument("--verbose", action="store_true", help="Show debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    config = load_config(args.config)
    run(config, args.source, args.dry_run)


if __name__ == "__main__":
    main()
