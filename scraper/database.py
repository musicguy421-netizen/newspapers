"""
database.py – Saves parsed articles as individual JSON files and maintains
              a master index file.
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ArticleDatabase:
    """Persists articles to JSON files and manages a master index."""

    def __init__(self, db_config: dict):
        self.output_dir = db_config.get("output_dir", "articles_db")
        self.index_file = db_config.get("index_file", "articles_db/index.json")
        os.makedirs(self.output_dir, exist_ok=True)
        self.index = self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, article: dict) -> bool:
        """
        Save *article* to disk.

        Returns True if the article was newly saved, False if it already
        existed (duplicate detected by article id / URL).
        """
        article_id = article["id"]
        if article_id in self.index:
            logger.debug("Skipping duplicate: %s", article["url"])
            return False

        filepath = os.path.join(self.output_dir, f"{article_id}.json")
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(article, fh, ensure_ascii=False, indent=2)

        self.index[article_id] = {
            "id": article_id,
            "url": article["url"],
            "source": article["source"],
            "title": article["title"],
            "published_date": article["published_date"],
            "scraped_at": article["scraped_at"],
            "keywords_matched": article["keywords_matched"],
            "file": filepath,
        }
        self._save_index()
        logger.info("Saved: %s", article["title"] or article["url"])
        return True

    def stats(self) -> dict:
        """Return basic counts from the index."""
        by_source: dict[str, int] = {}
        for entry in self.index.values():
            src = entry["source"]
            by_source[src] = by_source.get(src, 0) + 1
        return {"total": len(self.index), "by_source": by_source}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> dict:
        if os.path.exists(self.index_file):
            with open(self.index_file, encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def _save_index(self) -> None:
        with open(self.index_file, "w", encoding="utf-8") as fh:
            json.dump(self.index, fh, ensure_ascii=False, indent=2)
