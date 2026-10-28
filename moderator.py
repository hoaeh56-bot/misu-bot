import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
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
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, last_free_case TIMESTAMP)")
    con.commit()
    cur.close()
    con.close()

def get_balance(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else 0

def change_balance(user_id, amount, username=None):
    con = get_db()
    cur = con.cursor()
    if not username:
        cur.execute("SELECT username FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        if row: username = row[0]
        
    cur.execute("""
        INSERT INTO users (user_id, username, balance) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + %s
    """, (user_id, username, amount, amount))
    con.commit()
    cur.close()
    con.close()

# === ФОН: Проверка заявок на вывод ===
async def check_withdrawals():
    logging.info("ФОНОВАЯ ЗАДАЧА ЗАПУЩЕНА")
    while True:
        try:
            con = get_db()
            cur = con.cursor()
            cur.execute("SELECT id, user_id, item_name FROM withdrawals WHERE status = 'pending' LIMIT 1")
            row = cur.fetchone()
            
            if row:
                w_id, u_id, item_name = row
                logging.info(f"НАЙДЕНА ЗАЯВКА: {u_id} - {item_name}")
                
                await bot.send_message(
                    1780243205, # Твой ID
                    f"📦 <b>ЗАЯВКА НА ВЫВОД!</b>\n\nИгрок (ID): <code>{u_id}</code>\nПредмет: <b>{item_name}</b>",
                    parse_mode="HTML"
                )
                cur.execute("UPDATE withdrawals SET status = 'done' WHERE id = %s", (w_id,))
                con.commit()
            
            cur.close()
            con.close()
        except Exception as e:
            logging.error(f"ОШИБКА ЗАЯВОК: {e}")
        
        await asyncio.sleep(3)

# === КОМАНДЫ ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    change_balance(message.from_user.id, 0, message.from_user.username)
    await message.answer("Привет! Бот работает.")

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"👤 Твой ID: <code>{message.from_user.id}</code>\nБаланс: <b>{bal}</b> 🎃", parse_mode="HTML")

# === ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не вырубался) ===
async def handle_ping(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"ВЕБ-СЕРВЕР ЗАПУЩЕН НА ПОРТУ {port}")

async def main():
    init_db()
    logging.info("БАЗА ДАННЫХ ПОДКЛЮЧЕНА")
    
    # Запускаем веб-сервер (чтобы Render видел порт)
    asyncio.create_task(start_web_server())
    
    # Запускаем фоновую проверку заявок
    asyncio.create_task(check_withdrawals())
    
    # Запускаем бота
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    
    logging.info("БОТ ЗАПУСКАЕТСЯ...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
