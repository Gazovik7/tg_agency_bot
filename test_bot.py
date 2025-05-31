#!/usr/bin/env python3
"""
Simple script to test Telegram bot and get user IDs
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get bot token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set")
    exit(1)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    full_name = message.from_user.full_name or "No name"
    
    response_text = f"""
🤖 Telegram Monitoring Bot

Ваша информация:
📋 ID: {user_id}
👤 Имя: {full_name}
🔗 Username: @{username}

Этот ID нужно добавить в конфигурацию системы как участника команды.
    """
    
    await message.answer(response_text)
    
    # Log user info for admin
    logger.info(f"User connected - ID: {user_id}, Name: {full_name}, Username: {username}")

@router.message()
async def handle_all_messages(message: types.Message):
    """Handle all other messages"""
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    full_name = message.from_user.full_name or "No name"
    text = message.text or "[Non-text message]"
    
    logger.info(f"Message from {full_name} (ID: {user_id}): {text}")
    
    await message.answer(f"Получено сообщение от {full_name} (ID: {user_id})")

async def main():
    """Main function"""
    dp.include_router(router)
    
    print("🚀 Запуск Telegram бота...")
    print("📱 Отправьте команду /start боту, чтобы получить ваш ID")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())