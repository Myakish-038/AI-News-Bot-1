"""Reddit parser for AI-related subreddits."""

import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import config

# Use public JSON endpoint (no OAuth required)
REDDIT_BASE = "https://www.reddit.com"


async def fetch_subreddit(session: aiohttp.ClientSession, subreddit: str) -> List[Dict]:
    """Fetch hot posts from a subreddit using public JSON API."""
    news_items = []
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.NEWS_MAX_AGE_HOURS)

    headers = {
        "User-Agent": config.REDDIT_USER_AGENT
    }

    try:
        url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit=25"
        async with session.get(url, headers=headers, timeout=15) as response:
            if response.status != 200:
                print(f"Error fetching r/{subreddit}: HTTP {response.status}")
                return []

            data = await response.json()

            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                # Skip stickied posts
                if post_data.get("stickied"):
                    continue

                # Check age
                created_utc = post_data.get("created_utc", 0)
                pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                if pub_date < cutoff_time:
                    continue

                # Get URL (either external link or reddit post)
                url = post_data.get("url", "")
                if post_data.get("is_self"):
                    url = f"https://reddit.com{post_data.get('permalink', '')}"

                title = post_data.get("title", "")
                score = post_data.get("score", 0)
                num_comments = post_data.get("num_comments", 0)

                # Skip low-engagement posts
                if score < 20:
                    continue

                # Get selftext preview if available
                description = post_data.get("selftext", "")[:300]
                if not description:
                    description = f"Score: {score} | Comments: {num_comments}"

                news_items.append({
                    "title": title,
                    "url": url,
                    "description": description,
                    "source": f"r/{subreddit}",
                    "category": "community",
                    "published": pub_date.isoformat(),
                    "score": score,
                })

    except asyncio.TimeoutError:
        print(f"Timeout fetching r/{subreddit}")
    except Exception as e:
        print(f"Error fetching r/{subreddit}: {e}")

    return news_items


async def fetch_reddit_news() -> List[Dict]:
    """Fetch news from all configured subreddits."""
    all_news = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_subreddit(session, sub) for sub in config.REDDIT_SUBREDDITS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                print(f"Reddit fetch error: {result}")

    # Sort by score and limit
    all_news.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"Fetched {len(all_news)} posts from Reddit")
    return all_news[:15]  # Limit to top 15
