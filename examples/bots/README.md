# Примеры ботов для Bot Runner

Эта директория содержит примеры ботов для тестирования Bot Runner.

## Примеры

### 1. Echo Bot (Simple режим, один файл)

Простой эхо-бот в одном файле.

```bash
avtomatika-bot start echo-bot --simple examples/bots/echo_bot.py \
    -r "aiogram>=3.0" \
    -e BOT_TOKEN=your_token
```

### 2. Multi-File Bot (Simple режим, несколько файлов)

Бот с разделением на несколько файлов.

```bash
avtomatika-bot start multi-bot --simple examples/bots/multi_file_bot/ \
    --entrypoint bot.py \
    -r "aiogram>=3.0" \
    -e BOT_TOKEN=your_token
```

### 3. Custom Bot (Custom режим с Dockerfile)

Бот с кастомным Dockerfile.

```bash
avtomatika-bot start custom-bot --custom examples/bots/custom_bot/ \
    -e BOT_TOKEN=your_token
```

## Получение BOT_TOKEN

1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

## Команды управления

```bash
# Список ботов
avtomatika-bot list

# Статус бота
avtomatika-bot status echo-bot

# Логи бота
avtomatika-bot logs echo-bot

# Остановка бота
avtomatika-bot stop echo-bot
```
