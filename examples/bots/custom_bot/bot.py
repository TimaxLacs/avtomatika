"""Пример бота с кастомным Dockerfile.

Запуск через CLI:
    avtomatika-bot start custom-bot --custom examples/bots/custom_bot/ \
        -e BOT_TOKEN=your_telegram_bot_token
"""

import asyncio
import logging
import os
import platform

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

# Создаём бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start."""
    logger.info(f"User {message.from_user.id} started the bot")
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Это Custom бот — пример бота с кастомным Dockerfile.\n\n"
        "Команды:\n"
        "/start - начать\n"
        "/system - системная информация\n"
        "/env - переменные окружения"
    )


@dp.message(Command("system"))
async def cmd_system(message: types.Message):
    """Системная информация."""
    info = (
        f"🖥 Системная информация:\n\n"
        f"• Python: {platform.python_version()}\n"
        f"• OS: {platform.system()} {platform.release()}\n"
        f"• Architecture: {platform.machine()}\n"
        f"• Processor: {platform.processor() or 'N/A'}\n"
    )
    await message.answer(info)


@dp.message(Command("env"))
async def cmd_env(message: types.Message):
    """Показать (безопасные) переменные окружения."""
    # Показываем только безопасные переменные
    safe_vars = ["HOME", "PATH", "LANG", "USER", "HOSTNAME"]
    env_info = "🌐 Переменные окружения:\n\n"
    
    for var in safe_vars:
        value = os.environ.get(var, "N/A")
        # Обрезаем длинные значения
        if len(value) > 50:
            value = value[:47] + "..."
        env_info += f"• {var}: {value}\n"
    
    await message.answer(env_info)


@dp.message()
async def echo_handler(message: types.Message):
    """Эхо-обработчик."""
    if message.text:
        await message.answer(f"📢 {message.text}")


async def main():
    """Запуск бота."""
    logger.info("Starting Custom Bot...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
