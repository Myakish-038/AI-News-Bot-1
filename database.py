"""Database module for storing sent news and avoiding duplicates."""

import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
import config


async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                source TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_url ON sent_news(url)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sent_at ON sent_news(sent_at)
        """)
        # Token usage tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_token_created ON token_usage(created_at)
        """)
        await db.commit()


async def is_news_sent(url: str) -> bool:
    """Check if news with given URL was already sent."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM sent_news WHERE url = ?", (url,)
        )
        result = await cursor.fetchone()
        return result is not None


async def mark_news_sent(url: str, title: str, source: str):
    """Mark news as sent."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_news (url, title, source) VALUES (?, ?, ?)",
            (url, title, source)
        )
        await db.commit()


async def cleanup_old_news(days: int = 30):
    """Remove news older than specified days."""
    cutoff = datetime.now() - timedelta(days=days)
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM sent_news WHERE sent_at < ?",
            (cutoff.isoformat(),)
        )
        await db.commit()


async def get_stats() -> dict:
    """Get database statistics."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM sent_news")
        total = (await cursor.fetchone())[0]

        today = datetime.now().date().isoformat()
        cursor = await db.execute(
            "SELECT COUNT(*) FROM sent_news WHERE DATE(sent_at) = ?",
            (today,)
        )
        today_count = (await cursor.fetchone())[0]

        return {
            "total_sent": total,
            "sent_today": today_count
        }


async def log_token_usage(input_tokens: int, output_tokens: int, cost_usd: float):
    """Log token usage for cost tracking."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO token_usage (input_tokens, output_tokens, cost_usd) VALUES (?, ?, ?)",
            (input_tokens, output_tokens, cost_usd)
        )
        await db.commit()


async def get_token_stats() -> dict:
    """Get token usage statistics for today and this week."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        today = datetime.now().date().isoformat()

        # Today's stats
        cursor = await db.execute("""
            SELECT COALESCE(SUM(input_tokens), 0),
                   COALESCE(SUM(output_tokens), 0),
                   COALESCE(SUM(cost_usd), 0)
            FROM token_usage
            WHERE DATE(created_at) = ?
        """, (today,))
        today_row = await cursor.fetchone()

        # This week's stats (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        cursor = await db.execute("""
            SELECT COALESCE(SUM(input_tokens), 0),
                   COALESCE(SUM(output_tokens), 0),
                   COALESCE(SUM(cost_usd), 0)
            FROM token_usage
            WHERE DATE(created_at) >= ?
        """, (week_ago,))
        week_row = await cursor.fetchone()

        # All time stats
        cursor = await db.execute("""
            SELECT COALESCE(SUM(input_tokens), 0),
                   COALESCE(SUM(output_tokens), 0),
                   COALESCE(SUM(cost_usd), 0)
            FROM token_usage
        """)
        total_row = await cursor.fetchone()

        return {
            "today": {
                "input_tokens": today_row[0],
                "output_tokens": today_row[1],
                "cost_usd": today_row[2]
            },
            "week": {
                "input_tokens": week_row[0],
                "output_tokens": week_row[1],
                "cost_usd": week_row[2]
            },
            "total": {
                "input_tokens": total_row[0],
                "output_tokens": total_row[1],
                "cost_usd": total_row[2]
            }
        }
