"""Translation and summarization module using OpenAI API."""

import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import config
import database

client: Optional[AsyncOpenAI] = None

# GPT-4o mini pricing (per 1M tokens)
PRICE_INPUT_PER_1M = 0.15   # $0.15 per 1M input tokens
PRICE_OUTPUT_PER_1M = 0.60  # $0.60 per 1M output tokens


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for token usage."""
    input_cost = (input_tokens / 1_000_000) * PRICE_INPUT_PER_1M
    output_cost = (output_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M
    return input_cost + output_cost


def get_client() -> AsyncOpenAI:
    """Get or create OpenAI client."""
    global client
    if client is None:
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return client


async def translate_and_summarize(news_item: Dict) -> Dict:
    """Translate title and create a brief Russian summary."""

    if not config.OPENAI_API_KEY:
        # If no API key, return original
        return news_item

    title = news_item.get("title", "")
    description = news_item.get("description", "")

    prompt = f"""Переведи заголовок новости на русский язык и напиши краткое описание (1-2 предложения) на русском.

Заголовок: {title}

Описание (если есть): {description}

Формат ответа:
Заголовок: [переведённый заголовок]
Описание: [краткое описание на русском, 1-2 предложения]"""

    try:
        openai_client = get_client()
        response = await openai_client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ты переводчик технических новостей об искусственном интеллекте. Переводи точно, сохраняя технические термины. Отвечай только в указанном формате."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3
        )

        result = response.choices[0].message.content.strip()

        # Track token usage
        usage = response.usage
        if usage:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            cost = calculate_cost(input_tokens, output_tokens)
            await database.log_token_usage(input_tokens, output_tokens, cost)

        # Parse response
        lines = result.split("\n")
        translated_title = title
        translated_description = description

        for line in lines:
            if line.startswith("Заголовок:"):
                translated_title = line.replace("Заголовок:", "").strip()
            elif line.startswith("Описание:"):
                translated_description = line.replace("Описание:", "").strip()

        return {
            **news_item,
            "title_ru": translated_title,
            "description_ru": translated_description,
            "title_original": title,
        }

    except Exception as e:
        print(f"Translation error for '{title[:50]}...': {e}")
        return {
            **news_item,
            "title_ru": title,  # Keep original if translation fails
            "description_ru": description,
            "title_original": title,
        }


async def translate_batch(news_items: List[Dict], batch_size: int = 5) -> List[Dict]:
    """Translate a batch of news items with rate limiting."""
    translated = []

    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i + batch_size]
        tasks = [translate_and_summarize(item) for item in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, dict):
                translated.append(result)
            elif isinstance(result, Exception):
                print(f"Translation batch error: {result}")

        # Small delay between batches to avoid rate limits
        if i + batch_size < len(news_items):
            await asyncio.sleep(0.5)

    return translated
