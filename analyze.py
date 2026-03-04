"""
analyze.py – Search saved articles for keywords and print translated summaries.

Usage:
    python analyze.py                        # use default articles_db/index.json
    python analyze.py --db articles_db/index.json
"""

import argparse
import json
import os
import re

from deep_translator import GoogleTranslator

KEYWORDS = [
    "Saisonarbeiter",
    "Erntehelfer",
    "Drittstaatenabkommen",
    "nicht-eu",
]


def load_index(index_file: str) -> dict:
    if not os.path.exists(index_file):
        raise FileNotFoundError(f"Index not found: {index_file}")
    with open(index_file, encoding="utf-8") as fh:
        return json.load(fh)


def load_article(filepath: str) -> dict:
    with open(filepath, encoding="utf-8") as fh:
        return json.load(fh)


def keywords_found(article: dict) -> list[str]:
    """Return which keywords appear in the article's title or full text."""
    haystack = " ".join([
        article.get("title", ""),
        article.get("full_text", ""),
    ]).lower()
    return [kw for kw in KEYWORDS if kw.lower() in haystack]


def translate(text: str) -> str:
    if not text or not text.strip():
        return "(no summary available)"
    try:
        return GoogleTranslator(source="auto", target="en").translate(text[:4999])
    except Exception as exc:
        return f"(translation failed: {exc})"


def main() -> None:
    parser = argparse.ArgumentParser(description="Keyword analysis of scraped articles")
    parser.add_argument("--db", default="articles_db/index.json", help="Path to index.json")
    args = parser.parse_args()

    index = load_index(args.db)
    print(f"Total articles in database: {len(index)}\n")

    matches = []
    for entry in index.values():
        filepath = entry.get("file", "")
        if not os.path.exists(filepath):
            continue
        article = load_article(filepath)
        found = keywords_found(article)
        if found:
            matches.append((article, found))

    print(f"Articles mentioning keywords: {len(matches)}")

    # Count per keyword
    counts: dict[str, int] = {kw: 0 for kw in KEYWORDS}
    for _, found in matches:
        for kw in found:
            counts[kw] += 1

    print("\nKeyword counts:")
    for kw, count in counts.items():
        print(f"  {kw}: {count}")

    print("\n" + "=" * 70)

    translator = GoogleTranslator(source="auto", target="en")

    for article, found in matches:
        title_en = translate(article.get("title", ""))
        summary_raw = article.get("summary", "") or article.get("meta_description", "")
        summary_en = translate(summary_raw)

        print(f"\nSOURCE  : {article.get('source', '')}")
        print(f"URL     : {article.get('url', '')}")
        print(f"DATE    : {article.get('published_date', 'unknown')}")
        print(f"TITLE   : {title_en}")
        print(f"KEYWORDS: {', '.join(found)}")
        print(f"SUMMARY : {summary_en}")
        print("-" * 70)


if __name__ == "__main__":
    main()
