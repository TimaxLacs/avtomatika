# 🤖 Avtomatika Bot CLI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)

**Мощный CLI для управления Telegram-ботами через Avtomatika**

[Быстрый старт](#-быстрый-старт) •
[Команды](#-команды) •
[Режимы деплоя](#-режимы-деплоя) •
[Примеры](#-примеры)

</div>

---

## ✨ Возможности

- 🚀 **Три режима деплоя**: простой код, Docker, Git репозиторий
- 📊 **Полное управление**: запуск, остановка, обновление, логи, статус
- 🔒 **Изоляция**: каждый бот в отдельном Docker-контейнере
- 📈 **Лимиты**: до 3 ботов на пользователя, 24 часа работы
- 🎨 **Красивый вывод**: цветной интерфейс с Rich

---

## 📦 Установка

```bash
pip install avtomatika-bot-cli
```

Или из исходников:
```bash
git clone https://github.com/YOUR_USERNAME/avtomatika-bot-cli.git
cd avtomatika-bot-cli
pip install -e .
```

---

## 🚀 Быстрый старт

### 1. Настройка окружения

```bash
export AVTOMATIKA_URL=http://your-orchestrator:8000
export AVTOMATIKA_TOKEN=your-client-token
```

### 2. Запуск простого бота

```bash
# Один файл
avtomatika-bot start my-bot --simple bot.py \
  -r "aiogram>=3.0" \
  -e "BOT_TOKEN=123:ABC..."

# Несколько файлов
avtomatika-bot start my-bot --simple bot.py handlers.py utils.py \
  -r "aiogram>=3.0,aiohttp" \
  -e "BOT_TOKEN=123:ABC..."
```

### 3. Проверка статуса

```bash
avtomatika-bot list      # Список всех ботов
avtomatika-bot status my-bot  # Статус конкретного бота
avtomatika-bot logs my-bot    # Логи бота
```

---

## 📋 Команды

| Команда | Описание |
|---------|----------|
| `start` | Запустить нового бота |
| `stop` | Остановить бота |
| `update` | Обновить код бота |
| `restart` | Перезапустить бота |
| `list` | Список всех ботов |
| `status` | Статус конкретного бота |
| `logs` | Логи бота |

---

## 🎯 Режимы деплоя

### 1️⃣ Simple Mode — Простой код

Идеально для быстрого старта. Отправляете Python-файлы напрямую.

```bash
# Один файл
avtomatika-bot start echo-bot --simple bot.py \
  -r "aiogram>=3.0" \
  -e "BOT_TOKEN=$BOT_TOKEN"

# Несколько файлов
avtomatika-bot start complex-bot --simple main.py handlers.py db.py \
  --entrypoint main.py \
  -r "aiogram>=3.0,sqlalchemy,aiosqlite" \
  -e "BOT_TOKEN=$BOT_TOKEN" \
  -e "DATABASE_URL=sqlite:///bot.db"

# Inline код
avtomatika-bot start mini-bot --simple --inline \
  --code 'from aiogram import Bot; print("Hello!")' \
  -r "aiogram>=3.0"
```

### 2️⃣ Custom Mode — Dockerfile

Полный контроль над окружением. Своя сборка образа.

```bash
# Из локальной директории
avtomatika-bot start custom-bot --custom ./my-bot-project/

# Из Git репозитория
avtomatika-bot start git-bot --git https://github.com/user/telegram-bot.git \
  --branch main \
  -e "BOT_TOKEN=$BOT_TOKEN"

# Из архива по URL
avtomatika-bot start archive-bot --custom https://example.com/bot.tar.gz
```

### 3️⃣ Image Mode — Готовый Docker-образ

Используйте готовый образ из registry.

```bash
# Публичный образ
avtomatika-bot start prod-bot --image ghcr.io/user/my-bot:v1.0 \
  -e "BOT_TOKEN=$BOT_TOKEN"

# Приватный registry
avtomatika-bot start private-bot --image registry.example.com/bot:latest \
  --registry-user myuser \
  --registry-pass mytoken \
  -e "BOT_TOKEN=$BOT_TOKEN"
```

---

## 📝 Примеры

### Echo-бот за 1 минуту

**bot.py:**
```python
import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я эхо-бот 🤖")

@dp.message()
async def echo(message: types.Message):
    await message.answer(message.text)

asyncio.run(dp.start_polling(bot))
```

**Запуск:**
```bash
avtomatika-bot start echo --simple bot.py \
  -r "aiogram>=3.0" \
  -e "BOT_TOKEN=123:ABC..."
```

---

### Сложный бот из Git

```bash
avtomatika-bot start ai-assistant \
  --git https://github.com/deep-assistant/telegram-bot \
  --entrypoint __main__.py \
  -e "TELEGRAM_TOKEN=$BOT_TOKEN" \
  -e "OPENROUTER_API_KEY=$OPENROUTER_KEY" \
  -e "PROXY_URL=https://api.example.com" \
  -e "IS_DEV=True"
```

---

### Управление ботом

```bash
# Просмотр логов в реальном времени
avtomatika-bot logs my-bot --follow

# Обновление кода
avtomatika-bot update my-bot --simple new_bot.py -r "aiogram>=3.0"

# Перезапуск
avtomatika-bot restart my-bot

# Остановка
avtomatika-bot stop my-bot
```

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `AVTOMATIKA_URL` | URL оркестратора | `http://localhost:8000` |
| `AVTOMATIKA_TOKEN` | Токен клиента | — (обязательно) |

### Аргументы командной строки

```
avtomatika-bot start BOT_ID [OPTIONS]

Options:
  --simple FILE [FILE ...]    Режим simple: файлы с кодом
  --custom PATH               Режим custom: директория с Dockerfile
  --git URL                   Режим custom: Git репозиторий
  --image IMAGE               Режим image: Docker образ
  --entrypoint FILE           Точка входа (по умолчанию: bot.py)
  -r, --requirements DEPS     Зависимости (файл или список через запятую)
  -e, --env KEY=VALUE         Переменные окружения (можно несколько)
  --branch BRANCH             Git ветка (по умолчанию: main)
  --registry-user USER        Логин для приватного registry
  --registry-pass PASS        Пароль для приватного registry
  -v, --verbose               Подробный вывод
```

---

## 🏗️ Архитектура

```
┌─────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  avtomatika-bot │────▶│    Orchestrator     │────▶│  Bot Runner      │
│      CLI        │     │   (Avtomatika)      │     │    Worker        │
└─────────────────┘     └─────────────────────┘     └──────────────────┘
                                                            │
                                                            ▼
                                                    ┌──────────────┐
                                                    │   Docker     │
                                                    │  Containers  │
                                                    │  (ваши боты) │
                                                    └──────────────┘
```

### Связанные репозитории

| Компонент | Описание | Репозиторий |
|-----------|----------|-------------|
| **Orchestrator** | Ядро системы, управление workflow | [avtomatika](https://github.com/YOUR_USERNAME/avtomatika) |
| **Bot Runner Worker** | Воркер для управления Docker-контейнерами | [avtomatika-bot-runner-worker](https://github.com/YOUR_USERNAME/avtomatika-bot-runner-worker) |
| **CLI** | Этот репозиторий | — |

---

## 🔒 Лимиты

| Параметр | Значение |
|----------|----------|
| Максимум ботов на пользователя | 3 |
| Максимальное время работы | 24 часа |
| RAM на контейнер | 256 MB |
| CPU на контейнер | 0.5 cores |

---

## 🐛 Отладка

### Бот не запускается

```bash
# Проверьте логи
avtomatika-bot logs my-bot --lines 100

# Проверьте статус
avtomatika-bot status my-bot
```

### Ошибка подключения

```bash
# Проверьте доступность оркестратора
curl $AVTOMATIKA_URL/_public/status
```

### Конфликт с другим экземпляром

Если видите `TelegramConflictError`:
```bash
# Остановите все боты с этим токеном
avtomatika-bot stop my-bot
# Подождите 10 секунд
sleep 10
# Запустите заново
avtomatika-bot start my-bot ...
```

---

## 📄 Лицензия

MIT License — используйте свободно!

---

<div align="center">

**[⬆ Наверх](#-avtomatika-bot-cli)**

Made with ❤️ by [YOUR_NAME]

</div>
