"""Telegram bot module for sending AI news digests."""

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from typing import List, Dict
import config
import database


def escape_markdown(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def format_news_item(item: Dict, index: int) -> str:
    """Format a single news item for Telegram message."""
    title = escape_html(item.get("title_ru", item.get("title", "")))
    description = escape_html(item.get("description_ru", item.get("description", "")))
    url = item.get("url", "")
    source = escape_html(item.get("source", ""))

    # Use HTML formatting (more reliable than MarkdownV2)
    formatted = f"<b>{index}. {title}</b>\n"

    if description:
        # Truncate long descriptions
        if len(description) > 200:
            description = description[:200] + "..."
        formatted += f"{description}\n"

    formatted += f"📰 {source}\n"
    formatted += f"🔗 <a href=\"{url}\">Читать</a>\n"

    return formatted


def format_digest(news_items: List[Dict]) -> List[str]:
    """Format full digest into multiple messages (Telegram has 4096 char limit)."""
    messages = []
    current_message = "🤖 <b>AI News Digest</b>\n\n"

    for i, item in enumerate(news_items, 1):
        formatted_item = format_news_item(item, i)

        # Check if adding this item exceeds limit
        if len(current_message) + len(formatted_item) + 50 > 4000:
            messages.append(current_message)
            current_message = f"<b>Продолжение...</b>\n\n"

        current_message += formatted_item + "\n"

    if current_message.strip():
        messages.append(current_message)

    return messages


async def send_digest(news_items: List[Dict]) -> bool:
    """Send news digest via NEWS bot."""
    if not config.TELEGRAM_NEWS_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured")
        return False

    bot = Bot(token=config.TELEGRAM_NEWS_BOT_TOKEN)

    try:
        messages = format_digest(news_items)

        for message in messages:
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

        # Mark all items as sent
        for item in news_items:
            await database.mark_news_sent(
                url=item.get("url", ""),
                title=item.get("title", ""),
                source=item.get("source", "")
            )

        print(f"Successfully sent news digest with {len(news_items)} items")
        return True

    except Exception as e:
        print(f"Error sending digest: {e}")
        return False


async def send_business_ideas(ideas_message: str) -> bool:
    """Send business ideas via IDEAS bot."""
    if not config.TELEGRAM_IDEAS_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("Ideas bot credentials not configured")
        return False

    if not ideas_message:
        print("No ideas to send")
        return False

    bot = Bot(token=config.TELEGRAM_IDEAS_BOT_TOKEN)

    try:
        # Split if message is too long
        if len(ideas_message) > 4000:
            # Send in chunks
            chunks = [ideas_message[i:i+4000] for i in range(0, len(ideas_message), 4000)]
            for chunk in chunks:
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHAT_ID,
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
        else:
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=ideas_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )

        print("Successfully sent business ideas")
        return True

    except Exception as e:
        print(f"Error sending business ideas: {e}")
        return False


# Bot command handlers
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Привет! Я бот для AI-новостей.\n\n"
        f"Твой Chat ID: <code>{chat_id}</code>\n\n"
        f"Команды:\n"
        f"/digest - Получить дайджест сейчас\n"
        f"/stats - Статистика новостей\n"
        f"/costs - Расходы на API\n"
        f"/sources - Список источников",
        parse_mode=ParseMode.HTML
    )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command."""
    stats = await database.get_stats()
    await update.message.reply_text(
        f"📊 <b>Статистика</b>\n\n"
        f"Всего отправлено: {stats['total_sent']}\n"
        f"Отправлено сегодня: {stats['sent_today']}",
        parse_mode=ParseMode.HTML
    )


async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sources command."""
    sources_list = "\n".join([f"• {feed['name']}" for feed in config.RSS_FEEDS])
    subreddits = ", ".join([f"r/{sub}" for sub in config.REDDIT_SUBREDDITS])

    await update.message.reply_text(
        f"📰 <b>Источники новостей</b>\n\n"
        f"<b>RSS-ленты:</b>\n{sources_list}\n\n"
        f"<b>Reddit:</b>\n{subreddits}\n\n"
        f"<b>+ Hacker News</b> (фильтр по AI)",
        parse_mode=ParseMode.HTML
    )


async def cmd_costs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /costs command - show API usage costs."""
    token_stats = await database.get_token_stats()

    today = token_stats["today"]
    week = token_stats["week"]
    total = token_stats["total"]

    await update.message.reply_text(
        f"💰 <b>Расходы на OpenAI API</b>\n\n"
        f"<b>Сегодня:</b>\n"
        f"  Токены: {today['input_tokens']:,} вх / {today['output_tokens']:,} вых\n"
        f"  Стоимость: <b>${today['cost_usd']:.4f}</b>\n\n"
        f"<b>За неделю:</b>\n"
        f"  Токены: {week['input_tokens']:,} вх / {week['output_tokens']:,} вых\n"
        f"  Стоимость: <b>${week['cost_usd']:.4f}</b>\n\n"
        f"<b>Всего:</b>\n"
        f"  Токены: {total['input_tokens']:,} вх / {total['output_tokens']:,} вых\n"
        f"  Стоимость: <b>${total['cost_usd']:.4f}</b>",
        parse_mode=ParseMode.HTML
    )


def create_bot_application() -> Application:
    """Create and configure the bot application."""
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("costs", cmd_costs))

    return app
