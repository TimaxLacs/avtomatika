"""Обработчики сообщений для Multi-File Bot."""

import logging
from aiogram import Dispatcher, types
from aiogram.filters import Command

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики."""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Обработчик команды /start."""
        logger.info(f"User {message.from_user.id} started the bot")
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Это Multi-File бот — пример бота с несколькими файлами.\n\n"
            "Команды:\n"
            "/start - начать\n"
            "/help - помощь\n"
            "/about - о боте"
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Обработчик команды /help."""
        await message.answer(
            "📖 Помощь\n\n"
            "Этот бот демонстрирует структуру проекта с несколькими файлами:\n"
            "• bot.py — главный файл\n"
            "• handlers.py — обработчики сообщений\n\n"
            "Такая структура удобна для больших проектов!"
        )
    
    @dp.message(Command("about"))
    async def cmd_about(message: types.Message):
        """Обработчик команды /about."""
        await message.answer(
            "ℹ️ О боте\n\n"
            "Multi-File Bot v1.0\n"
            "Пример для Avtomatika Bot Runner\n\n"
            "Исходный код: examples/bots/multi_file_bot/"
        )
    
    @dp.message()
    async def echo(message: types.Message):
        """Эхо-обработчик."""
        if message.text:
            await message.answer(f"Вы написали: {message.text}")
        else:
            await message.answer("Интересное сообщение! 🤔")
    
    logger.info("Handlers registered successfully")
