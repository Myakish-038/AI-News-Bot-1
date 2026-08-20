"""Business ideas analyzer - extracts top 3 money-making ideas from news."""

import json
from typing import List, Dict
from openai import AsyncOpenAI
import config
import database

# GPT-4o mini pricing
PRICE_INPUT_PER_1M = 0.15
PRICE_OUTPUT_PER_1M = 0.60


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000) * PRICE_INPUT_PER_1M + \
           (output_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M


async def analyze_business_ideas(news_items: List[Dict]) -> str:
    """Analyze news and extract top 3 business ideas."""

    if not config.OPENAI_API_KEY or not news_items:
        return None

    # Prepare news summary for analysis
    news_summary = "\n\n".join([
        f"**{item.get('title_ru', item.get('title', ''))}**\n{item.get('description_ru', item.get('description', ''))}"
        for item in news_items[:20]  # Limit to top 20 for context
    ])

    prompt = f"""Проанализируй эти AI-новости и выбери 3 самые перспективные бизнес-идеи, на которых можно заработать.

НОВОСТИ:
{news_summary}

Для каждой идеи укажи:
1. Название идеи (короткое, цепляющее)
2. Суть: что конкретно делать (2-3 предложения)
3. Почему выстрелит: почему это актуально и востребовано прямо сейчас
4. Как заработать: конкретная модель монетизации
5. Первый шаг: что сделать уже сегодня, чтобы начать

Фокусируйся на:
- Идеях, которые можно реализовать быстро (недели, не месяцы)
- Низкий порог входа (минимум вложений)
- Реальный спрос (люди готовы платить)
- Тренды, которые только набирают обороты

Формат ответа - строго JSON:
{{
  "ideas": [
    {{
      "title": "Название идеи",
      "what": "Суть идеи",
      "why": "Почему выстрелит",
      "money": "Как заработать",
      "first_step": "Первый шаг"
    }}
  ]
}}"""

    try:
        client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Ты опытный предприниматель и аналитик AI-рынка. Ты умеешь находить золотые возможности в новостях и превращать их в бизнес-идеи. Отвечай только на русском языке. Отвечай строго в JSON формате."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        result = response.choices[0].message.content.strip()

        # Track tokens
        usage = response.usage
        if usage:
            cost = calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            await database.log_token_usage(usage.prompt_tokens, usage.completion_tokens, cost)

        # Parse and format
        data = json.loads(result)
        return format_ideas_message(data.get("ideas", []))

    except Exception as e:
        print(f"Error analyzing business ideas: {e}")
        return None


def format_ideas_message(ideas: List[Dict]) -> str:
    """Format ideas into a Telegram message."""
    if not ideas:
        return None

    message = "💡 <b>ТОП-3 БИЗНЕС-ИДЕИ ДНЯ</b>\n\n"

    for i, idea in enumerate(ideas[:3], 1):
        message += f"{'🥇' if i == 1 else '🥈' if i == 2 else '🥉'} <b>{idea.get('title', 'Идея')}</b>\n\n"
        message += f"📌 <b>Что делать:</b>\n{idea.get('what', '')}\n\n"
        message += f"🚀 <b>Почему выстрелит:</b>\n{idea.get('why', '')}\n\n"
        message += f"💰 <b>Как заработать:</b>\n{idea.get('money', '')}\n\n"
        message += f"👉 <b>Первый шаг:</b>\n{idea.get('first_step', '')}\n\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    return message
