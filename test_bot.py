"""Простой тестовый Telegram бот."""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Настройка подробного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8466887146:AAFn-N0w0MLMYQlMetAq_4IU5xdrq_Bj9kw"

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    logger.info(f"=== RECEIVED /start from {message.from_user.id} ===")
    try:
        result = await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Я тестовый бот Avtomatika. Вот что я умею:\n\n"
            "📝 /start - начать\n"
            "🏓 /ping - проверка связи\n"
            "ℹ️ /info - информация о боте\n"
            "💬 Любое сообщение - эхо"
        )
        logger.info(f"=== SENT response: {result} ===")
    except Exception as e:
        logger.error(f"=== ERROR sending message: {e} ===")
        raise


@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    """Обработчик команды /ping."""
    logger.info(f"=== RECEIVED /ping from {message.from_user.id} ===")
    try:
        result = await message.answer("🏓 Pong! Бот работает!")
        logger.info(f"=== SENT pong: {result} ===")
    except Exception as e:
        logger.error(f"=== ERROR: {e} ===")
        raise


@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    """Обработчик команды /info."""
    bot_info = await bot.get_me()
    await message.answer(
        f"📊 Информация о боте:\n\n"
        f"• Имя: {bot_info.first_name}\n"
        f"• Username: @{bot_info.username}\n"
        f"• ID: {bot_info.id}\n\n"
        f"👤 Ваша информация:\n"
        f"• Chat ID: {message.chat.id}\n"
        f"• User ID: {message.from_user.id}\n"
        f"• Username: @{message.from_user.username or 'N/A'}"
    )


@dp.message()
async def echo_handler(message: types.Message):
    """Эхо-обработчик для всех остальных сообщений."""
    logger.info(f"=== RECEIVED message from {message.from_user.id}: {message.text} ===")
    if message.text:
        await message.answer(f"📢 Вы написали:\n{message.text}")
    elif message.sticker:
        await message.answer_sticker(message.sticker.file_id)
    elif message.photo:
        await message.answer("📷 Красивое фото!")
    else:
        await message.answer("🤔 Интересное сообщение!")


async def main():
    """Запуск бота."""
    print("=" * 50)
    print("Starting Avtomatika Test Bot...")
    print("=" * 50)
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    print(f"Bot: @{bot_info.username}")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    print()
    
    # Удаляем webhook и старые сообщения
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
