# moderator.py
import asyncio
import logging
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

import config
from relationship import router as relationship_router

# Подключение к API Мисуграма
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.BOT_TOKEN, session=session)
dp = Dispatcher()

# --- ХЕНДЛЕР СТАРТА ---
@dp.message(CommandStart())
async def cmd_start(message: Message, db: asyncpg.Pool):
    await db.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        message.from_user.id, message.from_user.username
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить в группу", url="https://t.me/celestianabot?startgroup=true")]
    ])

    await message.answer(
        "Привет, я Селестиана! 💖\n"
        "Я помогаю строить отношения в чатах.\n"
        "Добавь меня в группу и напиши `.мойпол м` или `.мойпол ж`, чтобы начать.",
        reply_markup=kb
    )

# --- ЗАПУСК ---
async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Сброс вебхука (обязательно, чтобы не было конфликтов)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Вебхуки сброшены.")
    except Exception as e:
        logging.error(f"Ошибка сброса вебхука: {e}")

    # Подключение к базе
    try:
        pool = await asyncpg.create_pool(config.DATABASE_URL)
        logging.info("Успешное подключение к базе Supabase!")
    except Exception as e:
        logging.error(f"ОШИБКА ПОДКЛЮЧЕНИЯ К БАЗЕ: {e}")
        return

    dp.include_router(relationship_router)
    dp["db"] = pool
    
    logging.info("Бот Мисуграма запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
