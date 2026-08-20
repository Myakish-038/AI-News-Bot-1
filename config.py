"""Configuration for AI News Bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings - Two bots
TELEGRAM_NEWS_BOT_TOKEN = os.getenv("TELEGRAM_NEWS_BOT_TOKEN")
TELEGRAM_IDEAS_BOT_TOKEN = os.getenv("TELEGRAM_IDEAS_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Backward compatibility
TELEGRAM_BOT_TOKEN = TELEGRAM_NEWS_BOT_TOKEN

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"

# Reddit settings (optional)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AINewsBot/1.0")

# Digest settings
DIGEST_HOUR = int(os.getenv("DIGEST_HOUR", "9"))
DIGEST_MINUTE = int(os.getenv("DIGEST_MINUTE", "0"))
MAX_NEWS_PER_DIGEST = int(os.getenv("MAX_NEWS_PER_DIGEST", "30"))

# News age limit (in hours)
NEWS_MAX_AGE_HOURS = 24

# RSS Sources - AI News
RSS_FEEDS = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "news"
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "category": "news"
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "news"
    },
    {
        "name": "Ars Technica AI",
        "url": "https://arstechnica.com/tag/artificial-intelligence/feed/",
        "category": "news"
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "category": "research"
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "category": "news"
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "category": "official"
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "official"
    },
    {
        "name": "Anthropic News",
        "url": "https://www.anthropic.com/news/rss",
        "category": "official"
    },
]

# Reddit subreddits to monitor
REDDIT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "LocalLLaMA",
    "ChatGPT",
    "ClaudeAI",
]

# HackerNews settings
HACKERNEWS_MIN_SCORE = 50  # Minimum points for a story
HACKERNEWS_KEYWORDS = [
    "AI", "GPT", "LLM", "Claude", "OpenAI", "Anthropic", "Gemini",
    "machine learning", "neural", "transformer", "diffusion",
    "ChatGPT", "Copilot", "artificial intelligence", "deep learning",
    "Llama", "Mistral", "AGI", "NVIDIA", "GPU", "inference"
]

# Database
DATABASE_PATH = "news_bot.db"
