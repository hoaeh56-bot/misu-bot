# moderator.py
import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.types import Message

import config
from relationship import router as relationship_router

# Подключение к API Мисуграма строго по докам
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))

bot = Bot(token=config.BOT_TOKEN, session=session)
dp = Dispatcher()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                gender TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS couples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user1_id INTEGER,
                user2_id INTEGER,
                sparks INTEGER DEFAULT 100,
                level INTEGER DEFAULT 1,
                is_premium BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'ACTIVE',
                offended_by INTEGER DEFAULT NULL
            )
        """)
        await db.commit()

# --- ХЕНДЛЕР СТАРТА ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (message.from_user.id, message.from_user.username)
        )
        await db.commit()

    await message.answer(
        "Привет! Бот отношений запущен.\n"
        "Для начала укажи свой пол: `.мойпол м` или `.мойпол ж`"
    )

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    
    dp.include_router(relationship_router)
    
    logging.info("Бот Мисуграма запущен. База данных готова.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
