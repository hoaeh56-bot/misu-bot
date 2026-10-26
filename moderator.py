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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("quotes")

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DB = "quotes.db"

# ========== БАЗА ДАННЫХ ==========
def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            author TEXT,
            text TEXT,
            created_at TEXT
        )
    """)
    con.commit()
    con.close()

def add_quote(chat_id: int, author: str, text: str):
    con = sqlite3.connect(DB)
    con.execute(
        "INSERT INTO quotes (chat_id, author, text, created_at) VALUES (?, ?, ?, ?)",
        (chat_id, author, text, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    con.commit()
    con.close()

def get_random_quote(chat_id: int):
    con = sqlite3.connect(DB)
    row = con.execute(
        "SELECT author, text, created_at FROM quotes WHERE chat_id = ? ORDER BY RANDOM() LIMIT 1",
        (chat_id,)
    ).fetchone()
    con.close()
    return row

def get_two_quotes(chat_id: int):
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT author, text FROM quotes WHERE chat_id = ? ORDER BY RANDOM() LIMIT 2",
        (chat_id,)
    ).fetchall()
    con.close()
    return rows

# ========== ВСТРОЕННЫЕ ШУТКИ ==========
JOKES = [
    "Программист — это машина для превращения кофе в код.",
    "Я не ленивый, я просто в энергосберегающем режиме.",
    "Мой код не багованный, это фича!",
    "Если долго смотреть в монитор, можно увидеть, как проходит жизнь.",
    "Я не толстый, это просто кэш от интернета.",
    "Всем привет, я тут просто мимо проходил.",
    "Работа не волк, в лес не убежит. А я убегу.",
    "Не откладывай на завтра то, что можно вообще не делать.",
    "Сон — это лучшее изобретение человечества.",
    "Лучший способ начать день — это не начинать его слишком рано.",
    "Ты не ты, когда голоден. А я всегда голоден.",
    "Мой IQ равен 100, но утром он падает до 10.",
    "Все проблемы решаются сном. Проверено.",
    "Я не опаздываю, я просто задерживаюсь в прошлом.",
    "Если что-то не получается — значит, это не твое.",
]

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-цитатник.\n\n"
        "Команды:\n"
        "/quote Текст цитаты — сохранить от своего имени\n"
        "/quote @ник Текст цитаты — сохранить от чужого имени\n"
        "/random — случайная цитата\n"
        "/joke — случайная шутка\n"
        "/mix — сгенерировать мем из цитат чата\n"
    )

@dp.message(Command("quote"))
async def cmd_quote(message: Message):
    # Получаем текст после команды /quote
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Напиши цитату! Пример:\n/quote Я тут главный\n/quote @user Я тут главный")
        return

    content = parts[1].strip()
    
    # Проверяем, начинается ли с @ника
    if content.startswith("@"):
        author_parts = content.split(maxsplit=1)
        author = author_parts[0]
        if len(author_parts) < 2:
            await message.reply("Ты указал ник, но забыл саму цитату!")
            return
        text = author_parts[1]
    else:
        # Если ник не указан, берем имя того, кто пишет
        user = message.from_user
        author = f"@{user.username}" if user.username else user.full_name
        text = content

    add_quote(message.chat.id, author, text)
    await message.reply(f"✅ Цитата сохранена! Автор: {author}")

@dp.message(Command("random"))
async def cmd_random(message: Message):
    row = get_random_quote(message.chat.id)
    if not row:
        await message.reply("В этом чате еще нет цитат. Добавь через /quote!")
        return

    author, text, date = row
    await message.answer(
        f"💬 **Цитата**\n\n"
        f"«{text}»\n\n"
        f"— {author} ({date})"
    )

@dp.message(Command("joke"))
async def cmd_joke(message: Message):
    joke = random.choice(JOKES)
    await message.answer(f"😂 {joke}")

@dp.message(Command("mix"))
async def cmd_mix(message: Message):
    rows = get_two_quotes(message.chat.id)
    if len(rows) < 2:
        await message.reply("Нужно минимум 2 цитаты для генерации. Добавь еще через /quote!")
        return

    (author1, text1), (author2, text2) = rows[0], rows[1]
    
    # Обрезаем слишком длинные тексты
    text1 = text1[:50] + "..." if len(text1) > 50 else text1
    text2 = text2[:50] + "..." if len(text2) > 50 else text2

    templates = [
        f"Встречаются как-то {author1} и {author2}.\n"
        f"{author1}: «{text1}»\n"
        f"{author2}: «{text2}»\n\n"
        f"И тут они поняли, что это не диалог, а диагноз.",

        f"Новый мем из чата:\n"
        f"«{text1}» + «{text2}» = {author1} и {author2} — легенды.",

        f"Если объединить {author1} и {author2}, получится:\n"
        f"«{text1} {text2}»\n\n"
        f"Не пытайтесь это понять, просто смейтесь.",

        f"Совет дня от {author1}: «{text1}».\n"
        f"Совет дня от {author2}: «{text2}».\n"
        f"Выбирай, кому верить.",
        
        f"Срочные новости! {author1} заявил: «{text1}».\n"
        f"Однако {author2} не согласен: «{text2}»."
    ]

    result = random.choice(templates)
    await message.answer(f"🎭 **Шутка дня**\n\n{result}")

async def main():
    init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
