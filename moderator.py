import asyncio
import logging
import random
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

DB = "quotes.db"

def init_db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY, chat_id INTEGER, author TEXT, text TEXT, created_at TEXT)")
    con.commit()
    con.close()

def add_quote(chat_id, author, text):
    con = sqlite3.connect(DB)
    con.execute("INSERT INTO quotes (chat_id, author, text, created_at) VALUES (?, ?, ?, ?)", (chat_id, author, text, datetime.now().strftime("%d.%m %H:%M")))
    con.commit()
    con.close()

def get_random(chat_id):
    con = sqlite3.connect(DB)
    row = con.execute("SELECT author, text, created_at FROM quotes WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1", (chat_id,)).fetchone()
    con.close()
    return row

def get_two(chat_id):
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT author, text FROM quotes WHERE chat_id = ? ORDER BY RANDOM() LIMIT 2", (chat_id,)).fetchall()
    con.close()
    return rows

JOKES = [
    "Программист — это машина для превращения кофе в код.",
    "Я не ленивый, я в энергосберегающем режиме.",
    "Мой код не багованный, это фича!",
    "Если долго смотреть в монитор, можно увидеть, как проходит жизнь.",
    "Я не толстый, это кэш от интернета.",
    "Работа не волк, в лес не убежит. А я убегу.",
    "Сон — лучшее изобретение человечества.",
    "Ты не ты, когда голоден. А я всегда голоден.",
]

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот-цитатник.\n\n/quote Текст - сохранить\n/random - случайная цитата\n/joke - шутка\n/mix - мем из цитат")

@dp.message(Command("quote"))
async def cmd_quote(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Напиши цитату после команды. Пример: /quote Я тут главный")
        return

    content = parts[1].strip()
    
    if content.startswith("@"):
        author_parts = content.split(maxsplit=1)
        author = author_parts[0]
        if len(author_parts) < 2:
            await message.answer("Ты указал ник, но забыл цитату!")
            return
        text = author_parts[1]
    else:
        user = message.from_user
        author = f"@{user.username}" if user.username else user.full_name
        text = content

    add_quote(message.chat.id, author, text)
    await message.answer(f"Цитата сохранена! Автор: {author}")

@dp.message(Command("random"))
async def cmd_random(message: Message):
    row = get_random(message.chat.id)
    if not row:
        await message.answer("В чате нет цитат. Добавь через /quote")
        return

    author, text, date = row
    await message.answer(f"Цитата:\n\n{text}\n\nАвтор: {author} ({date})")

@dp.message(Command("joke"))
async def cmd_joke(message: Message):
    await message.answer(random.choice(JOKES))

@dp.message(Command("mix"))
async def cmd_mix(message: Message):
    rows = get_two(message.chat.id)
    if len(rows) < 2:
        await message.answer("Нужно минимум 2 цитаты для генерации. Добавь еще!")
        return

    (author1, text1), (author2, text2) = rows[0], rows[1]
    text1 = text1[:50] + "..." if len(text1) > 50 else text1
    text2 = text2[:50] + "..." if len(text2) > 50 else text2

    templates = [
        f"Встречаются {author1} и {author2}.\n{author1}: {text1}\n{author2}: {text2}\n\nДиагноз.",
        f"Новый мем:\n{text1} + {text2} = {author1} и {author2}",
        f"Совет от {author1}: {text1}.\nСовет от {author2}: {text2}.",
        f"Новости: {author1} заявил: {text1}.\nА {author2} не согласен: {text2}."
    ]

    await message.answer(f"Шутка дня:\n\n{random.choice(templates)}")

async def main():
    init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
