# AI News Bot 🤖

Telegram-бот для ежедневного дайджеста AI-новостей с переводом на русский язык.

## Возможности

- 📰 Сбор новостей из 9+ источников (TechCrunch, The Verge, VentureBeat и др.)
- 🔍 Мониторинг Hacker News (фильтр по AI-тематике)
- 💬 Мониторинг Reddit (r/MachineLearning, r/LocalLLaMA и др.)
- 🌐 Автоматический перевод на русский (OpenAI GPT-4o mini)
- 🗓 Ежедневная отправка дайджеста в Telegram
- 🔄 Дедупликация новостей (не повторяет уже отправленные)

## Быстрый старт

### 1. Клонирование и установка

```bash
cd ai-news-bot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Создание Telegram-бота

1. Напиши [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Следуй инструкциям, получи **токен бота**
4. Запусти бота и отправь `/start` - бот покажет твой **Chat ID**

### 3. Получение OpenAI API Key

1. Зайди на [platform.openai.com](https://platform.openai.com)
2. Создай API key в разделе API Keys
3. Пополни баланс (минимум $5, хватит на несколько месяцев)

### 4. Настройка

```bash
cp .env.example .env
```

Отредактируй `.env`:

```env
TELEGRAM_BOT_TOKEN=твой_токен_от_botfather
TELEGRAM_CHAT_ID=твой_chat_id
OPENAI_API_KEY=sk-...

# Опционально
DIGEST_HOUR=9        # Час отправки дайджеста (0-23)
DIGEST_MINUTE=0      # Минуты
MAX_NEWS_PER_DIGEST=30
```

### 5. Запуск

```bash
# Тестовый запуск (отправит дайджест сразу)
python main.py --now

# Полный запуск с планировщиком
python main.py

# Только бот (без автоматической рассылки)
python main.py --bot
```

## Команды бота

- `/start` - Показать Chat ID и справку
- `/digest` - Получить дайджест прямо сейчас
- `/stats` - Статистика отправленных новостей
- `/sources` - Список источников

## Запуск на сервере (beget)

### Через systemd

Создай файл `/etc/systemd/system/ai-news-bot.service`:

```ini
[Unit]
Description=AI News Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/ai-news-bot
ExecStart=/path/to/ai-news-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl enable ai-news-bot
sudo systemctl start ai-news-bot
sudo systemctl status ai-news-bot
```

### Через screen/tmux

```bash
screen -S newsbot
python main.py
# Ctrl+A, D для выхода из screen
```

## Настройка источников

Редактируй `config.py`:

```python
# Добавить RSS-ленту
RSS_FEEDS = [
    ...
    {
        "name": "Новый источник",
        "url": "https://example.com/feed.xml",
        "category": "news"  # news, research, official
    },
]

# Добавить subreddit
REDDIT_SUBREDDITS = [
    ...
    "NewSubreddit",
]

# Изменить ключевые слова для HackerNews
HACKERNEWS_KEYWORDS = [
    "AI", "GPT", ...
]
```

## Структура проекта

```
ai-news-bot/
├── main.py           # Точка входа, планировщик
├── config.py         # Настройки и источники
├── bot.py            # Telegram бот
├── processor.py      # Обработка и фильтрация
├── translator.py     # Перевод через OpenAI
├── database.py       # SQLite хранилище
├── sources/
│   ├── rss.py        # RSS-парсер
│   ├── hackernews.py # HackerNews API
│   └── reddit.py     # Reddit API
├── requirements.txt
├── .env.example
└── README.md
```

## Стоимость

При использовании GPT-4o mini для 30 новостей в день:
- **~$0.30/месяц**

Telegram Bot API бесплатен.

## Troubleshooting

**Бот не отправляет сообщения:**
- Проверь Chat ID (должен быть числом)
- Убедись, что написал боту `/start`

**Нет перевода:**
- Проверь OPENAI_API_KEY
- Проверь баланс на platform.openai.com

**Мало новостей:**
- Увеличь `NEWS_MAX_AGE_HOURS` в config.py
- Добавь больше источников
