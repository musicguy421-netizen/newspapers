"""
fetcher.py – Discovers article URLs from RSS feeds or direct HTML scraping.
"""

import time
import logging
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ArticleFetcher:
    """Discovers candidate article URLs from configured sources."""

    def __init__(self, settings: dict):
        self.delay = settings.get("request_delay_seconds", 2)
        self.timeout = settings.get("request_timeout_seconds", 15)
        self.max_articles = settings.get("max_articles_per_source", 50)
        self.headers = {
            "User-Agent": settings.get(
                "user_agent", "ResearchScraper/1.0 (Academic Research)"
            )
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_article_urls(self, source: dict) -> list[str]:
        """Return a list of article URLs for the given source config."""
        source_type = source.get("type", "rss")
        if source_type == "rss" and source.get("rss_url"):
            return self._urls_from_rss(source)
        elif source_type == "scrape":
            return self._urls_from_html(source)
        else:
            logger.warning("Unknown source type or missing rss_url for '%s'", source["name"])
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _urls_from_rss(self, source: dict) -> list[str]:
        rss_url = source["rss_url"]
        logger.info("Fetching RSS feed: %s", rss_url)
        try:
            feed = feedparser.parse(rss_url)
        except Exception as exc:
            logger.error("Failed to parse RSS feed %s: %s", rss_url, exc)
            return []

        urls = []
        for entry in feed.entries[: self.max_articles]:
            link = entry.get("link")
            if link:
                urls.append(link)

        logger.info("Found %d URLs from RSS: %s", len(urls), source["name"])
        return urls

    def _urls_from_html(self, source: dict) -> list[str]:
        selector = source.get("article_link_selector", "a")
        attr = source.get("article_link_attribute", "href")
        base = source["base_url"]
        next_selector = source.get("next_page_selector", "a[rel='next']")
        max_pages = source.get("max_pages", 10)

        current_url = source.get("article_list_url", base)
        seen: set[str] = set()
        urls: list[str] = []
        page = 1

        while current_url and page <= max_pages and len(urls) < self.max_articles:
            logger.info("Scraping page %d: %s", page, current_url)
            html = self._get(current_url)
            if html is None:
                break

            soup = BeautifulSoup(html, "lxml")

            # Collect article links from this page
            for tag in soup.select(selector):
                link = tag.get(attr)
                if not link:
                    continue
                full = link if urlparse(link).scheme else urljoin(base, link)
                if full not in seen:
                    seen.add(full)
                    urls.append(full)
                if len(urls) >= self.max_articles:
                    break

            # Find next page link
            next_tag = soup.select_one(next_selector)
            if next_tag and next_tag.get("href"):
                next_href = next_tag["href"]
                next_url = next_href if urlparse(next_href).scheme else urljoin(current_url, next_href)
                if next_url == current_url:
                    break  # avoid infinite loop
                current_url = next_url
                page += 1
            else:
                break

        logger.info("Found %d URLs from HTML scrape (%d page(s)): %s", len(urls), page, source["name"])
        return urls

    def _get(self, url: str) -> str | None:
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            time.sleep(self.delay)
            return resp.text
        except requests.RequestException as exc:
            logger.error("HTTP request failed for %s: %s", url, exc)
            return None
