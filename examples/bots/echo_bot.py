"""Простой Echo бот для тестирования Bot Runner.

Запуск через CLI:
    avtomatika-bot start echo-bot --simple examples/bots/echo_bot.py \
        -r "aiogram>=3.0" \
        -e BOT_TOKEN=your_telegram_bot_token
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Токен из переменной окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

# Номер теста (опционально)
TEST_NUMBER = os.environ.get("TEST_NUMBER", "N/A")

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    logger.info(f"User {message.from_user.id} started the bot")
    
    test_info = f"🧪 **Тест #{TEST_NUMBER}**\n\n" if TEST_NUMBER != "N/A" else ""
    
    await message.answer(
        f"{test_info}"
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я Echo-бот. Отправь мне любое сообщение, и я его повторю.\n\n"
        "Команды:\n"
        "/start - начать\n"
        "/ping - проверка связи\n"
        "/info - информация о боте",
        parse_mode="Markdown"
    )


@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    """Обработчик команды /ping."""
    await message.answer("🏓 Pong!")


@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    """Обработчик команды /info."""
    await message.answer(
        "📊 Информация о боте:\n\n"
        f"• Chat ID: {message.chat.id}\n"
        f"• User ID: {message.from_user.id}\n"
        f"• Username: @{message.from_user.username or 'N/A'}\n"
        f"• Bot: @{(await bot.get_me()).username}"
    )


@dp.message()
async def echo_handler(message: types.Message):
    """Эхо-обработчик для всех остальных сообщений."""
    if message.text:
        logger.info(f"Echo message from {message.from_user.id}: {message.text[:50]}")
        await message.answer(f"📢 Вы сказали:\n{message.text}")
    elif message.sticker:
        await message.answer_sticker(message.sticker.file_id)
    elif message.photo:
        await message.answer("📷 Красивое фото!")
    else:
        await message.answer("🤔 Интересное сообщение!")


async def main():
    """Запуск бота."""
    logger.info("Starting Echo Bot...")
    
    # Удаляем webhook на случай если он был установлен
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
