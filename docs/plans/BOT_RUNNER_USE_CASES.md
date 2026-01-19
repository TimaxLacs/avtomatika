# Сценарии использования Bot Runner

Этот документ описывает различные сценарии использования системы Bot Runner.

## Содержание

1. [Simple режим](#simple-режим)
2. [Custom режим](#custom-режим)
3. [Image режим](#image-режим)
4. [Управление ботами](#управление-ботами)
5. [Интеграции](#интеграции)
6. [Особые случаи](#особые-случаи)

---

## Simple режим

### 1. Минимальный Echo бот

```bash
avtomatika-bot start echo --simple bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=123:ABC
```

`bot.py`:
```python
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

@dp.message()
async def echo(message: Message):
    await message.answer(message.text)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
```

### 2. Бот с несколькими файлами

```bash
avtomatika-bot start my-bot --simple bot.py handlers.py config.py \
  --entrypoint bot.py \
  -r "aiogram>=3.0,aiohttp" \
  -e BOT_TOKEN=123:ABC
```

### 3. Бот из директории

```bash
avtomatika-bot start my-bot --simple ./my_bot_project/ \
  --entrypoint main.py \
  -r requirements.txt \
  -e BOT_TOKEN=123:ABC
```

### 4. Inline код (для быстрых тестов)

```bash
avtomatika-bot start test --simple --inline \
  --code 'import os; from aiogram import Bot, Dispatcher; print("Bot started!")' \
  -e BOT_TOKEN=123:ABC
```

### 5. Бот с базой данных

```bash
avtomatika-bot start db-bot --simple bot.py database.py models.py \
  -r "aiogram>=3.0,aiosqlite,sqlalchemy[asyncio]" \
  -e BOT_TOKEN=123:ABC \
  -e DATABASE_URL=sqlite:///bot.db
```

### 6. Бот с внешним API

```bash
avtomatika-bot start api-bot --simple bot.py api_client.py \
  -r "aiogram>=3.0,aiohttp,pydantic" \
  -e BOT_TOKEN=123:ABC \
  -e API_KEY=secret_api_key \
  -e API_URL=https://api.example.com
```

---

## Custom режим

### 7. Бот с кастомным Dockerfile

```bash
avtomatika-bot start custom-bot --custom ./my_project/ \
  -e BOT_TOKEN=123:ABC
```

Структура проекта:
```
my_project/
├── Dockerfile
├── requirements.txt
├── bot.py
└── utils/
    └── helpers.py
```

### 8. Бот из Git репозитория

```bash
avtomatika-bot start git-bot --git https://github.com/user/telegram-bot.git \
  --branch main \
  -e BOT_TOKEN=123:ABC
```

### 9. Бот из приватного Git репозитория

```bash
avtomatika-bot start private-bot \
  --git https://user:token@github.com/user/private-bot.git \
  -e BOT_TOKEN=123:ABC
```

### 10. Бот из GitLab

```bash
avtomatika-bot start gitlab-bot \
  --git https://gitlab.com/user/bot.git \
  --branch develop \
  -e BOT_TOKEN=123:ABC
```

### 11. Бот из tar.gz архива (URL)

```bash
avtomatika-bot start archive-bot \
  --custom https://example.com/releases/bot-v1.0.tar.gz \
  -e BOT_TOKEN=123:ABC
```

### 12. Бот с системными зависимостями

`Dockerfile`:
```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
avtomatika-bot start media-bot --custom ./media_bot/ \
  -e BOT_TOKEN=123:ABC
```

### 13. Бот с ML моделью

```bash
avtomatika-bot start ml-bot --custom ./ml_bot/ \
  -e BOT_TOKEN=123:ABC \
  -e MODEL_PATH=/app/models/classifier.pkl
```

---

## Image режим

### 14. Готовый Docker образ

```bash
avtomatika-bot start prebuilt --image myuser/telegram-bot:v1.0 \
  -e BOT_TOKEN=123:ABC
```

### 15. Образ из GitHub Container Registry

```bash
avtomatika-bot start ghcr-bot --image ghcr.io/user/bot:latest \
  --registry-user myuser \
  --registry-pass ghp_xxxx \
  -e BOT_TOKEN=123:ABC
```

### 16. Образ из приватного registry

```bash
avtomatika-bot start private-image \
  --image registry.example.com/bots/mybot:v2 \
  --registry-user deploy \
  --registry-pass secret123 \
  -e BOT_TOKEN=123:ABC
```

### 17. Образ из Docker Hub

```bash
avtomatika-bot start dockerhub-bot \
  --image username/my-telegram-bot:stable \
  -e BOT_TOKEN=123:ABC \
  -e DEBUG=true
```

---

## Управление ботами

### 18. Список всех ботов

```bash
avtomatika-bot list
```

Вывод:
```
┌─────────────────────────────────────────────────────┐
│                  Боты (2/3)                         │
├────────────┬─────────────┬─────────────────────────┤
│ Bot ID     │ Статус      │ Запущен                 │
├────────────┼─────────────┼─────────────────────────┤
│ echo-bot   │ 🟢 running  │ 2024-01-15T10:30:00Z    │
│ parser-bot │ 🟢 running  │ 2024-01-15T09:15:00Z    │
└────────────┴─────────────┴─────────────────────────┘
```

### 19. Статус конкретного бота

```bash
avtomatika-bot status echo-bot
```

### 20. Просмотр логов

```bash
# Последние 100 строк
avtomatika-bot logs echo-bot

# Последние 50 строк
avtomatika-bot logs echo-bot -n 50
```

### 21. Остановка бота

```bash
avtomatika-bot stop echo-bot
```

### 22. Перезапуск бота

```bash
avtomatika-bot stop my-bot
avtomatika-bot start my-bot --simple bot.py -r "aiogram>=3.0" -e BOT_TOKEN=123:ABC
```

---

## Интеграции

### 23. Бот с Redis

```bash
avtomatika-bot start redis-bot --simple bot.py \
  -r "aiogram>=3.0,aioredis" \
  -e BOT_TOKEN=123:ABC \
  -e REDIS_URL=redis://redis:6379/0
```

### 24. Бот с PostgreSQL

```bash
avtomatika-bot start pg-bot --custom ./pg_bot/ \
  -e BOT_TOKEN=123:ABC \
  -e DATABASE_URL=postgresql://user:pass@db:5432/botdb
```

### 25. Бот с Webhook (через ngrok)

```bash
avtomatika-bot start webhook-bot --simple bot.py \
  -r "aiogram>=3.0,aiohttp" \
  -e BOT_TOKEN=123:ABC \
  -e WEBHOOK_URL=https://abc123.ngrok.io/webhook \
  -e WEBHOOK_PORT=8080
```

### 26. Бот с S3 хранилищем

```bash
avtomatika-bot start s3-bot --simple bot.py storage.py \
  -r "aiogram>=3.0,aiobotocore" \
  -e BOT_TOKEN=123:ABC \
  -e S3_ENDPOINT=https://s3.example.com \
  -e S3_ACCESS_KEY=xxx \
  -e S3_SECRET_KEY=yyy \
  -e S3_BUCKET=bot-files
```

### 27. Бот с Prometheus метриками

```bash
avtomatika-bot start metrics-bot --custom ./metrics_bot/ \
  -e BOT_TOKEN=123:ABC \
  -e METRICS_PORT=9090
```

---

## Особые случаи

### 28. Бот-парсер (долгоживущий)

```bash
avtomatika-bot start parser --simple parser_bot.py \
  -r "aiogram>=3.0,telethon,vk-api" \
  -e BOT_TOKEN=123:ABC \
  -e TG_API_ID=xxx \
  -e TG_API_HASH=yyy \
  -e VK_TOKEN=zzz
```

### 29. Бот с scheduled tasks

```bash
avtomatika-bot start scheduler-bot --simple bot.py scheduler.py \
  -r "aiogram>=3.0,apscheduler" \
  -e BOT_TOKEN=123:ABC \
  -e TZ=Europe/Moscow
```

### 30. Мультиязычный бот

```bash
avtomatika-bot start i18n-bot --simple bot.py i18n/ \
  --entrypoint bot.py \
  -r "aiogram>=3.0,babel" \
  -e BOT_TOKEN=123:ABC \
  -e DEFAULT_LOCALE=ru
```

### 31. Бот с админ-панелью

```bash
avtomatika-bot start admin-bot --custom ./admin_bot/ \
  -e BOT_TOKEN=123:ABC \
  -e ADMIN_IDS=123456789,987654321 \
  -e WEB_PORT=8000
```

### 32. Тестовый бот (с debug логами)

```bash
avtomatika-bot start debug-bot --simple bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=123:ABC \
  -e DEBUG=true \
  -e LOG_LEVEL=DEBUG
```

---

## Примечания

### Лимиты

- Максимум 3 бота на пользователя
- Максимальное время работы: 24 часа
- Память: 256 MB на контейнер
- CPU: 0.5 ядра на контейнер

### Безопасность

- Все контейнеры изолированы
- Доступ только к сети Docker
- Секреты передаются через переменные окружения
- Контейнеры запускаются без root прав

### Рекомендации

1. **Всегда указывайте версии зависимостей** — избегайте `aiogram` без версии
2. **Используйте переменные окружения для секретов** — не храните токены в коде
3. **Логируйте важные события** — это поможет при отладке
4. **Обрабатывайте исключения** — бот не должен падать от ошибок
