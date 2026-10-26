import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

import config

logging.basicConfig(level=logging.INFO)
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DB = "stats.db"

def init_db():
    con = sqlite3.connect(DB)
    # Таблица для сообщений
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            date TEXT
        )
    """)
    # Таблица для чатов, куда надо присылать итоги
    con.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY
        )
    """)
    con.commit()
    con.close()

def register_chat(chat_id):
    con = sqlite3.connect(DB)
    con.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (chat_id,))
    con.commit()
    con.close()

def get_all_chats():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT chat_id FROM chats").fetchall()
    con.close()
    return [row[0] for row in rows]

def add_message(chat_id, user_id, user_name):
    today = datetime.now().strftime("%Y-%m-%d")
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO messages (chat_id, user_id, user_name, date) VALUES (?, ?, ?, ?)", (chat_id, user_id, user_name, today))
    con.commit()
    con.close()

def get_top(chat_id):
    today = datetime.now().strftime("%Y-%m-%d")
    con = sqlite3.connect(DB)
    rows = con.execute("""
        SELECT user_name, COUNT(*) as msg_count 
        FROM messages 
        WHERE chat_id = ? AND date = ? 
        GROUP BY user_id 
        ORDER BY msg_count DESC 
        LIMIT 3
    """, (chat_id, today)).fetchall()
    con.close()
    return rows

def clear_old():
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM messages WHERE date < date('now', '-2 days')")
    con.commit()
    con.close()

# --- КОМАНДЫ ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    register_chat(message.chat.id) # Запоминаем чат
    await message.answer("Бот-статистика активен!\n/top - топ за сегодня\nВ 21:30 пришлю итоги.")

@dp.message(Command("top"))
async def cmd_top(message: Message):
    register_chat(message.chat.id)
    top = get_top(message.chat.id)
    if not top:
        await message.answer("Сегодня еще никто не писал. Будь первым!")
        return
    
    text = "🏆 Топ активности за сегодня:\n\n"
    for i, (name, count) in enumerate(top):
        text += f"{i+1}. {name} — {count} сообщений\n"
        
    await message.answer(text)

# --- СЧЕТЧИК ---
@dp.message(F.text)
async def count_messages(message: Message):
    register_chat(message.chat.id) # Запоминаем любой чат, где пишут
    if message.text.startswith("/"):
        return
    user = message.from_user
    name = f"@{user.username}" if user.username else user.full_name
    add_message(message.chat.id, user.id, name)

# --- АВТО-РАССЫЛКА В 21:30 ---
async def daily_summary():
    while True:
        now = datetime.now()
        # Если сейчас 21:30
        if now.hour == 21 and now.minute == 30:
            chats = get_all_chats()
            for chat_id in chats:
                top = get_top(chat_id)
                if top:
                    text = "📢 Ежедневный итог!\n\n"
                    text += "Топ-3 самых активных сегодня:\n\n"
                    rewards = ["500 монет", "300 монет", "100 монет"]
                    
                    for i, (name, count) in enumerate(top):
                        text += f"{i+1} место: {name} — {count} сообщений (выиграл {rewards[i]})\n"
                        
                    try:
                        await bot.send_message(chat_id, text)
                    except Exception as e:
                        logging.error(f"Не удалось отправить в чат {chat_id}: {e}")
            
            # Ждем минуту, чтобы не спамить
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(20)

async def main():
    init_db()
    clear_old()
    asyncio.create_task(daily_summary()) # Запускаем таймер
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
