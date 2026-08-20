"""News processor: fetches, filters, deduplicates, and prepares news for digest."""

import asyncio
from typing import List, Dict
from datetime import datetime
from urllib.parse import urlparse
import database
from sources import fetch_rss_news, fetch_hackernews, fetch_reddit_news
from translator import translate_batch
import config


def deduplicate_by_url(news_items: List[Dict]) -> List[Dict]:
    """Remove duplicate news items by URL."""
    seen_urls = set()
    unique_items = []

    for item in news_items:
        url = item.get("url", "")
        # Normalize URL (remove trailing slash, query params for comparison)
        parsed = urlparse(url)
        normalized = f"{parsed.netloc}{parsed.path}".rstrip("/").lower()

        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique_items.append(item)

    return unique_items


def normalize_title(title: str) -> str:
    """Normalize title for comparison: lowercase, remove punctuation, common words."""
    import re
    # Remove punctuation and extra spaces
    title = re.sub(r'[^\w\s]', ' ', title.lower())
    title = re.sub(r'\s+', ' ', title).strip()

    # Remove common stop words that don't help with deduplication
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'and', 'or', 'but', 'not', 'this', 'that', 'it', 'its',
                  'как', 'что', 'это', 'для', 'на', 'с', 'в', 'и', 'не'}

    words = [w for w in title.split() if w not in stop_words and len(w) > 2]
    return ' '.join(words)


def deduplicate_by_title_similarity(news_items: List[Dict], threshold: float = 0.5) -> List[Dict]:
    """Remove news with similar titles using multiple methods."""
    unique_items = []

    for item in news_items:
        title = item.get("title", "")
        normalized = normalize_title(title)
        title_words = set(normalized.split())

        is_duplicate = False
        for existing in unique_items:
            existing_title = existing.get("title", "")
            existing_normalized = normalize_title(existing_title)
            existing_words = set(existing_normalized.split())

            # Method 1: Jaccard similarity
            if title_words and existing_words:
                intersection = len(title_words & existing_words)
                union = len(title_words | existing_words)
                similarity = intersection / union

                if similarity > threshold:
                    is_duplicate = True
                    break

            # Method 2: One title contains most of the other
            if title_words and existing_words:
                overlap = len(title_words & existing_words)
                min_len = min(len(title_words), len(existing_words))
                if min_len > 0 and overlap / min_len > 0.8:
                    is_duplicate = True
                    break

            # Method 3: Substring match (for very similar titles)
            if len(normalized) > 20 and len(existing_normalized) > 20:
                if normalized in existing_normalized or existing_normalized in normalized:
                    is_duplicate = True
                    break

        if not is_duplicate:
            unique_items.append(item)

    return unique_items


def sort_by_relevance(news_items: List[Dict]) -> List[Dict]:
    """Sort news by relevance and recency."""

    def score_item(item: Dict) -> float:
        score = 0.0

        # Boost official sources
        source = item.get("source", "").lower()
        if any(x in source for x in ["openai", "anthropic", "google ai"]):
            score += 100

        # Boost by engagement (if available)
        score += item.get("score", 0) * 0.1

        # Boost by category
        category = item.get("category", "")
        if category == "official":
            score += 50
        elif category == "research":
            score += 30
        elif category == "news":
            score += 20

        # Boost recent items
        published = item.get("published")
        if published:
            try:
                pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                hours_ago = (datetime.now(pub_date.tzinfo) - pub_date).total_seconds() / 3600
                score += max(0, 24 - hours_ago)  # More recent = higher score
            except Exception:
                pass

        return score

    return sorted(news_items, key=score_item, reverse=True)


async def filter_already_sent(news_items: List[Dict]) -> List[Dict]:
    """Filter out news that was already sent."""
    filtered = []
    for item in news_items:
        url = item.get("url", "")
        if not await database.is_news_sent(url):
            filtered.append(item)
    return filtered


async def fetch_all_news() -> List[Dict]:
    """Fetch news from all sources."""
    print("Fetching news from all sources...")

    # Fetch from all sources in parallel
    rss_task = fetch_rss_news()
    hn_task = fetch_hackernews()
    reddit_task = fetch_reddit_news()

    results = await asyncio.gather(
        rss_task, hn_task, reddit_task,
        return_exceptions=True
    )

    all_news = []
    for result in results:
        if isinstance(result, list):
            all_news.extend(result)
        elif isinstance(result, Exception):
            print(f"Source fetch error: {result}")

    print(f"Total fetched: {len(all_news)} items")
    return all_news


async def process_news() -> List[Dict]:
    """Main processing pipeline: fetch, filter, dedupe, translate, sort."""

    # Step 1: Fetch from all sources
    all_news = await fetch_all_news()

    if not all_news:
        print("No news fetched")
        return []

    # Step 2: Deduplicate by URL
    unique_news = deduplicate_by_url(all_news)
    print(f"After URL dedup: {len(unique_news)} items")

    # Step 3: Deduplicate by title similarity
    unique_news = deduplicate_by_title_similarity(unique_news)
    print(f"After title dedup: {len(unique_news)} items")

    # Step 4: Filter already sent
    new_news = await filter_already_sent(unique_news)
    print(f"After filtering sent: {len(new_news)} items")

    if not new_news:
        print("No new news to send")
        return []

    # Step 5: Sort by relevance
    sorted_news = sort_by_relevance(new_news)

    # Step 6: Limit to max items
    limited_news = sorted_news[:config.MAX_NEWS_PER_DIGEST]
    print(f"Limited to: {len(limited_news)} items")

    # Step 7: Translate
    if config.OPENAI_API_KEY:
        print("Translating news...")
        translated_news = await translate_batch(limited_news)
        print(f"Translated: {len(translated_news)} items")
        return translated_news

    return limited_news
