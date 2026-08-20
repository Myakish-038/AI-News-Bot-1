"""RSS feed parser for AI news."""

import asyncio
import feedparser
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dateutil import parser as date_parser
import config


async def fetch_feed(session: aiohttp.ClientSession, feed_info: dict) -> List[Dict]:
    """Fetch and parse a single RSS feed."""
    news_items = []

    try:
        async with session.get(feed_info["url"], timeout=30) as response:
            if response.status != 200:
                print(f"Error fetching {feed_info['name']}: HTTP {response.status}")
                return []

            content = await response.text()
            feed = feedparser.parse(content)

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.NEWS_MAX_AGE_HOURS)

            for entry in feed.entries[:20]:  # Limit entries per feed
                try:
                    # Parse publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'published'):
                        pub_date = date_parser.parse(entry.published)
                        if pub_date.tzinfo is None:
                            pub_date = pub_date.replace(tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                    # Skip old news
                    if pub_date and pub_date < cutoff_time:
                        continue

                    # Extract description/summary
                    description = ""
                    if hasattr(entry, 'summary'):
                        description = entry.summary
                    elif hasattr(entry, 'description'):
                        description = entry.description

                    # Clean HTML from description
                    import re
                    description = re.sub(r'<[^>]+>', '', description)
                    description = description.strip()[:500]  # Limit length

                    news_items.append({
                        "title": entry.title,
                        "url": entry.link,
                        "description": description,
                        "source": feed_info["name"],
                        "category": feed_info.get("category", "news"),
                        "published": pub_date.isoformat() if pub_date else None,
                    })

                except Exception as e:
                    print(f"Error parsing entry from {feed_info['name']}: {e}")
                    continue

    except asyncio.TimeoutError:
        print(f"Timeout fetching {feed_info['name']}")
    except Exception as e:
        print(f"Error fetching {feed_info['name']}: {e}")

    return news_items


async def fetch_rss_news() -> List[Dict]:
    """Fetch news from all configured RSS feeds."""
    all_news = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_feed(session, feed) for feed in config.RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                print(f"Feed fetch error: {result}")

    print(f"Fetched {len(all_news)} news from RSS feeds")
    return all_news
