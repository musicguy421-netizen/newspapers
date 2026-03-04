"""
parser.py – Downloads a single article URL and extracts its full text,
            then checks whether any of the configured keywords appear in it.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone

import requests
from newspaper import Article, ArticleException

logger = logging.getLogger(__name__)


class ArticleParser:
    """Downloads and parses individual article pages."""

    def __init__(self, settings: dict, keywords: list[str]):
        self.delay = settings.get("request_delay_seconds", 2)
        self.timeout = settings.get("request_timeout_seconds", 15)
        self.keywords = [kw.lower() for kw in keywords]
        self.user_agent = settings.get(
            "user_agent", "ResearchScraper/1.0 (Academic Research)"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, url: str, source_name: str) -> dict | None:
        """
        Download and parse *url*.

        Returns a dict with article data if at least one keyword is found,
        or None if the article should be skipped.
        """
        article = self._download(url)
        if article is None:
            return None

        text = article.text or ""
        title = article.title or ""

        # Keyword matching – check title + body (case-insensitive).
        combined = (title + " " + text).lower()
        matched = [kw for kw in self.keywords if kw in combined]
        if not matched:
            return None

        pub_date = self._format_date(article.publish_date)

        return {
            "id": self._make_id(url),
            "url": url,
            "source": source_name,
            "title": title,
            "authors": article.authors,
            "published_date": pub_date,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "keywords_matched": matched,
            "full_text": text,
            "summary": article.summary,
            "top_image": article.top_image,
            "meta_description": article.meta_description,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _download(self, url: str) -> Article | None:
        try:
            article = Article(url, browser_user_agent=self.user_agent)
            article.download()
            time.sleep(self.delay)
            article.parse()
            article.nlp()
            return article
        except ArticleException as exc:
            logger.warning("newspaper3k failed for %s: %s", url, exc)
            return None
        except requests.RequestException as exc:
            logger.warning("Network error for %s: %s", url, exc)
            return None
        except Exception as exc:
            logger.warning("Unexpected error parsing %s: %s", url, exc)
            return None

    @staticmethod
    def _make_id(url: str) -> str:
        return hashlib.sha1(url.encode()).hexdigest()[:12]

    @staticmethod
    def _format_date(dt) -> str | None:
        if dt is None:
            return None
        if hasattr(dt, "isoformat"):
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        return str(dt)
