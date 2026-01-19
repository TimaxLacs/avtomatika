"""
Echo Bot v2 - Обновлённая версия для тестирования update.
Добавлена команда /version для проверки версии.
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
VERSION = os.environ.get("BOT_VERSION", "V2")  # Новая переменная

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обновлённый обработчик /start."""
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        f"🆕 **ОБНОВЛЁННЫЙ БОТ {VERSION}**\n\n"
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Доступные команды:\n"
        "/start - начать\n"
        "/ping - проверка связи\n"
        "/version - текущая версия\n"
        "/info - информация о боте",
        parse_mode="Markdown"
    )


@dp.message(Command("ping"))
async def cmd_ping(message: types.Message):
    """Проверка связи."""
    await message.answer("🏓 Pong! (v2)")


@dp.message(Command("version"))
async def cmd_version(message: types.Message):
    """Новая команда - показать версию."""
    await message.answer(f"📦 Версия бота: **{VERSION}**", parse_mode="Markdown")


@dp.message(Command("info"))
async def cmd_info(message: types.Message):
    """Информация о боте."""
    bot_info = await bot.get_me()
    await message.answer(
        f"🤖 Бот: @{bot_info.username}\n"
        f"📦 Версия: {VERSION}\n"
        f"👤 Твой ID: {message.from_user.id}"
    )


@dp.message()
async def echo_handler(message: types.Message):
    """Эхо сообщений с пометкой версии."""
    if message.text:
        logger.info(f"Echo (v2): {message.text}")
        await message.answer(f"[v2] Ты написал: {message.text}")


async def main():
    logger.info(f"Starting Echo Bot {VERSION}...")
    logger.info("=" * 50)
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot: @{bot_info.username}")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
