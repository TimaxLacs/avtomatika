"""Пример бота с несколькими файлами.

Запуск через CLI:
    avtomatika-bot start multi-bot --simple examples/bots/multi_file_bot/ \
        --entrypoint bot.py \
        -r "aiogram>=3.0" \
        -e BOT_TOKEN=your_telegram_bot_token
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from handlers import register_handlers

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


async def main():
    """Запуск бота."""
    logger.info("Starting Multi-File Bot...")
    
    # Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем обработчики из отдельного модуля
    register_handlers(dp)
    
    # Удаляем webhook на случай если он был установлен
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаем polling
    try:
        logger.info("Bot is running!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
