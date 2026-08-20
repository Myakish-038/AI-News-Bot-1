#!/usr/bin/env python3
"""
AI News Bot - Main entry point.

A Telegram bot that collects AI news from multiple sources,
translates them to Russian, and sends daily digests.

Usage:
    python main.py              # Run with scheduler (production)
    python main.py --now        # Send digest immediately (testing)
    python main.py --bot        # Run bot with commands only (no scheduler)
"""

import asyncio
import argparse
import sys
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
import database
from processor import process_news
from bot import send_digest, send_business_ideas, create_bot_application
from ideas_analyzer import analyze_business_ideas


async def send_daily_digest():
    """Process and send news + business ideas."""
    print(f"\n{'='*50}")
    print(f"Starting digest at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    try:
        # Process news
        news_items = await process_news()

        if not news_items:
            print("No news to send today")
            return

        # 1. Send NEWS via first bot
        print("Sending news digest...")
        news_success = await send_digest(news_items)
        if news_success:
            print(f"News sent: {len(news_items)} items")

        # 2. Analyze and send BUSINESS IDEAS via second bot
        print("Analyzing business ideas...")
        ideas_message = await analyze_business_ideas(news_items)
        if ideas_message:
            print("Sending business ideas...")
            ideas_success = await send_business_ideas(ideas_message)
            if ideas_success:
                print("Business ideas sent!")
        else:
            print("No business ideas generated")

        # Cleanup old records
        await database.cleanup_old_news(days=30)

    except Exception as e:
        print(f"Error in daily digest: {e}")
        import traceback
        traceback.print_exc()


async def run_with_scheduler():
    """Run the bot with scheduled daily digests."""
    print("Initializing AI News Bot...")

    # Check configuration
    if not config.TELEGRAM_NEWS_BOT_TOKEN:
        print("ERROR: TELEGRAM_NEWS_BOT_TOKEN not set")
        sys.exit(1)

    if not config.TELEGRAM_IDEAS_BOT_TOKEN:
        print("WARNING: TELEGRAM_IDEAS_BOT_TOKEN not set - ideas won't be sent")

    if not config.TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    if not config.OPENAI_API_KEY:
        print("WARNING: OPENAI_API_KEY not set - translations will be skipped")

    # Initialize database
    await database.init_db()
    print("Database initialized")

    # Setup scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_daily_digest,
        CronTrigger(hour=config.DIGEST_HOUR, minute=config.DIGEST_MINUTE),
        id="daily_digest",
        name="Daily AI News Digest",
        replace_existing=True
    )
    scheduler.start()

    print(f"Scheduler started. Digest will be sent daily at {config.DIGEST_HOUR:02d}:{config.DIGEST_MINUTE:02d}")

    # Create and run bot application
    app = create_bot_application()

    # Add command to trigger digest manually
    from telegram.ext import CommandHandler
    from telegram import Update
    from telegram.ext import ContextTypes

    async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual digest trigger."""
        await update.message.reply_text("⏳ Собираю новости...")
        await send_daily_digest()
        await update.message.reply_text("✅ Дайджест отправлен!")

    app.add_handler(CommandHandler("digest", cmd_digest))

    print("Bot is running. Press Ctrl+C to stop.")

    # Run the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        scheduler.shutdown()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


async def run_now():
    """Send digest immediately (for testing)."""
    print("Running immediate digest...")

    # Check configuration
    if not config.TELEGRAM_NEWS_BOT_TOKEN:
        print("ERROR: TELEGRAM_NEWS_BOT_TOKEN not set")
        sys.exit(1)

    if not config.TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    # Initialize database
    await database.init_db()

    # Send digest + ideas
    await send_daily_digest()


async def run_bot_only():
    """Run bot without scheduler (commands only)."""
    print("Running bot in command-only mode...")

    if not config.TELEGRAM_NEWS_BOT_TOKEN:
        print("ERROR: TELEGRAM_NEWS_BOT_TOKEN not set")
        sys.exit(1)

    await database.init_db()

    app = create_bot_application()

    # Add manual digest command
    from telegram.ext import CommandHandler
    from telegram import Update
    from telegram.ext import ContextTypes

    async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("⏳ Собираю новости...")
        await send_daily_digest()
        await update.message.reply_text("✅ Готово!")

    app.add_handler(CommandHandler("digest", cmd_digest))

    print("Bot is running in command mode. Send /start to begin.")

    # Initialize and start polling manually
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    parser = argparse.ArgumentParser(description="AI News Bot")
    parser.add_argument("--now", action="store_true", help="Send digest immediately")
    parser.add_argument("--bot", action="store_true", help="Run bot without scheduler")
    args = parser.parse_args()

    if args.now:
        asyncio.run(run_now())
    elif args.bot:
        asyncio.run(run_bot_only())
    else:
        asyncio.run(run_with_scheduler())


if __name__ == "__main__":
    main()
