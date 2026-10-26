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
TARGET_CHAT_ID = -10022  # Тот самый чат MisuGram

# ========== БАЗА ДАННЫХ ==========
def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            date TEXT
        )
    """)
    con.commit()
    con.close()

def add_message(chat_id, user_id, user_name):
    today = datetime.now().strftime("%Y-%m-%d")
    con = sqlite3.connect(DB)
    con.execute(
        "INSERT INTO messages (chat_id, user_id, user_name, date) VALUES (?, ?, ?, ?)",
        (chat_id, user_id, user_name, today)
    )
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

def clear_old_messages():
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM messages WHERE date < date('now', '-7 days')")
    con.commit()
    con.close()

# ========== ЛОВИМ ВСЕ СООБЩЕНИЯ ==========
@dp.message(F.text)
async def count_messages(message: Message):
    if message.text.startswith("/"):
        return
    
    user = message.from_user
    name = f"@{user.username}" if user.username else user.full_name
    add_message(message.chat.id, user.id, name)

# ========== КОМАНДА /top ==========
@dp.message(Command("top"))
async def cmd_top(message: Message):
    top = get_top(message.chat.id)
    if not top:
        await message.answer("Сегодня еще никто не писал. Будь первым!")
        return
    
    text = "🏆 Топ активности за сегодня:\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (name, count) in enumerate(top):
        text += f"{medals[i]} {name} — {count} сообщений\n"
        
    await message.answer(text)

# ========== АВТОМАТИЧЕСКИЙ ИТОГ В 21:30 ==========
async def daily_summary():
    while True:
        now = datetime.now()
        if now.hour == 21 and now.minute == 30:
            top = get_top(TARGET_CHAT_ID)
            if top:
                text = "📢 Ежедневный итог в 21:30!\n\n"
                text += "Топ-3 самых активных сегодня:\n\n"
                medals = ["🥇 1 место", "🥈 2 место", "🥉 3 место"]
                rewards = ["500 монет", "300 монет", "100 монет"]
                
                for i, (name, count) in enumerate(top):
                    text += f"{medals[i]}: {name} (выиграл {rewards[i]})\n"
                    
                try:
                    await bot.send_message(TARGET_CHAT_ID, text)
                except Exception as e:
                    logging.error(f"Ошибка отправки итогов: {e}")
            
            # Ждем минуту, чтобы не спамить
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(20)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я считаю активность.\n"
        "/top — топ-3 за сегодня\n"
        "В 21:30 подвожу итоги!"
    )

async def main():
    init_db()
    clear_old_messages()
    
    # Запускаем таймер в фоне
    asyncio.create_task(daily_summary())
    
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
