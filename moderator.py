import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import psycopg2
import config

logging.basicConfig(level=logging.INFO)

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    con = get_db()
    cur = con.cursor()
    # Создаем таблицу кошельков, если ее нет
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            usdt_balance NUMERIC DEFAULT 0,
            gram_balance NUMERIC DEFAULT 0,
            sol_balance NUMERIC DEFAULT 0,
            trx_balance NUMERIC DEFAULT 0
        )
    """)
    con.commit()
    cur.close()
    con.close()

def get_or_create_user(user_id, username=None):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))
        con.commit()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    con.close()
    return row

@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Создаем кошелек, если его нет
    get_or_create_user(message.from_user.id, message.from_user.username)
    
    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кошелек", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "Добро пожаловать в Crypto Bot.\n"
        "Ваш кошелек создан. Нажмите кнопку ниже, чтобы открыть приложение.",
        reply_markup=kb
    )

async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()

async def main():
    init_db()
    asyncio.create_task(start_web_server())
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
