"""HackerNews API parser for AI-related stories."""

import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import config

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


def is_ai_related(title: str) -> bool:
    """Check if title contains AI-related keywords."""
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in config.HACKERNEWS_KEYWORDS)


async def fetch_story(session: aiohttp.ClientSession, story_id: int) -> Optional[Dict]:
    """Fetch a single story from HackerNews."""
    try:
        async with session.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=10) as response:
            if response.status != 200:
                return None
            return await response.json()
    except Exception:
        return None


async def fetch_hackernews() -> List[Dict]:
    """Fetch AI-related stories from HackerNews."""
    news_items = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.NEWS_MAX_AGE_HOURS)

    async with aiohttp.ClientSession() as session:
        # Get top stories
        try:
            async with session.get(f"{HN_API_BASE}/topstories.json", timeout=15) as response:
                if response.status != 200:
                    print(f"Error fetching HN top stories: HTTP {response.status}")
                    return []
                story_ids = await response.json()
        except Exception as e:
            print(f"Error fetching HN top stories: {e}")
            return []

        # Fetch stories in batches
        batch_size = 30
        for i in range(0, min(len(story_ids), 200), batch_size):
            batch_ids = story_ids[i:i + batch_size]
            tasks = [fetch_story(session, sid) for sid in batch_ids]
            stories = await asyncio.gather(*tasks)

            for story in stories:
                if not story or story.get("type") != "story":
                    continue

                title = story.get("title", "")
                score = story.get("score", 0)
                url = story.get("url", "")
                story_time = story.get("time", 0)

                # Skip if no URL (self posts)
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story.get('id')}"

                # Check score threshold
                if score < config.HACKERNEWS_MIN_SCORE:
                    continue

                # Check if AI-related
                if not is_ai_related(title):
                    continue

                # Check age
                pub_date = datetime.fromtimestamp(story_time, tz=timezone.utc)
                if pub_date < cutoff_time:
                    continue

                news_items.append({
                    "title": title,
                    "url": url,
                    "description": f"HN Score: {score} | Comments: {story.get('descendants', 0)}",
                    "source": "Hacker News",
                    "category": "community",
                    "published": pub_date.isoformat(),
                    "score": score,
                })

    # Sort by score
    news_items.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"Fetched {len(news_items)} AI-related stories from HackerNews")
    return news_items[:15]  # Limit to top 15
