# Avtomatika Bot CLI

CLI клиент для управления ботами через Avtomatika Bot Runner.

## Установка

```bash
pip install -e .
```

## Использование

### Настройка

```bash
# Через переменные окружения
export AVTOMATIKA_URL=http://localhost:8000
export AVTOMATIKA_TOKEN=your-client-token

# Или через аргументы
avtomatika-bot --url http://localhost:8000 --token your-token list
```

### Запуск бота

#### Simple режим (один файл)
```bash
avtomatika-bot start my-bot --simple bot.py \
  -r "aiogram>=3.0" \
  -e BOT_TOKEN=123:ABC...
```

#### Simple режим (несколько файлов)
```bash
avtomatika-bot start my-bot --simple bot.py handlers.py utils/ \
  --entrypoint bot.py \
  -r "aiogram>=3.0,aiohttp" \
  -e BOT_TOKEN=123:ABC...
```

#### Custom режим (директория)
```bash
avtomatika-bot start my-bot --custom ./my-project/ \
  -e BOT_TOKEN=123:ABC...
```

#### Custom режим (Git)
```bash
avtomatika-bot start my-bot --git https://github.com/user/bot.git \
  --branch main \
  -e BOT_TOKEN=123:ABC...
```

#### Image режим
```bash
avtomatika-bot start my-bot --image ghcr.io/user/bot:v1 \
  --registry-user myuser \
  --registry-pass ghp_xxx \
  -e BOT_TOKEN=123:ABC...
```

### Управление ботами

```bash
# Список ботов
avtomatika-bot list

# Статус бота
avtomatika-bot status my-bot

# Логи бота
avtomatika-bot logs my-bot
avtomatika-bot logs my-bot -n 50

# Остановка бота
avtomatika-bot stop my-bot
```

## Команды

| Команда | Описание |
|---------|----------|
| `start` | Запустить бота |
| `stop` | Остановить бота |
| `logs` | Получить логи |
| `list` | Список ботов |
| `status` | Статус бота |
