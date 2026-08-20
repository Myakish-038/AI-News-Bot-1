#!/usr/bin/env python3
"""Quick stats check without running the full bot."""

import asyncio
import database


async def main():
    await database.init_db()

    print("📊 Статистика новостей:")
    stats = await database.get_stats()
    print(f"  Всего отправлено: {stats['total_sent']}")
    print(f"  Отправлено сегодня: {stats['sent_today']}")

    print("\n💰 Расходы на OpenAI API:")
    token_stats = await database.get_token_stats()

    today = token_stats["today"]
    week = token_stats["week"]
    total = token_stats["total"]

    print(f"\n  Сегодня:")
    print(f"    Токены: {today['input_tokens']:,} вх / {today['output_tokens']:,} вых")
    print(f"    Стоимость: ${today['cost_usd']:.4f}")

    print(f"\n  За неделю:")
    print(f"    Токены: {week['input_tokens']:,} вх / {week['output_tokens']:,} вых")
    print(f"    Стоимость: ${week['cost_usd']:.4f}")

    print(f"\n  Всего:")
    print(f"    Токены: {total['input_tokens']:,} вх / {total['output_tokens']:,} вых")
    print(f"    Стоимость: ${total['cost_usd']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
