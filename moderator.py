import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import psycopg2

import config

logging.basicConfig(level=logging.INFO)
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

# =========================================================
# ССЫЛКА НА БАЗУ (Session Pooler - работает на Render)
# =========================================================
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0
        )
    """)
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
    cur.execute("""
        INSERT INTO users (user_id, username, balance) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + %s
    """, (user_id, username, amount, amount))
    con.commit()
    cur.close()
    con.close()

# ========== КОМАНДЫ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    change_balance(message.from_user.id, 0, message.from_user.username)
    
    # Кнопка для открытия Мини-Аппа
    web_app_url = "https://misu-site.vercel.app/" 
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎃 Открыть игру", web_app=WebAppInfo(url=web_app_url))]
    ])
    
    await message.answer(
        "Привет! Это бот для пополнения баланса.\n\n"
        "/profile - узнать свой ID и баланс\n"
        "/buy 100 - купить 100 тыкв за Stars 🎃\n\n"
        "Жми кнопку ниже, чтобы открыть кейсы!",
        reply_markup=kb
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    
    text = (
        f"👤 <b>Твой профиль</b>\n\n"
        f"ID (для сайта): <code>{user_id}</code>\n"
        f"Баланс: <b>{bal}</b> тыкв 🎃"
    )
    await message.answer(text, parse_mode="HTML")

# ========== ПОКУПКА ЗА STARS ==========
@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Напиши количество: /buy 100")
        return
    
    amount = int(parts[1])
    if amount < 10:
        await message.answer("Минимум 10 тыкв.")
        return

    # Курс: 100 тыкв = 550 звезд (т.е. 5.5 за штуку)
    stars_price = int(amount * 5.5)

    await message.answer_invoice(
        title=f"Покупка {amount} тыкв",
        description=f"Покупка {amount} тыкв за {stars_price} звёзд.",
        payload=f"buy_{amount}",
        provider_token="", 
        currency="XTR", 
        prices=[LabeledPrice(label="XTR", amount=stars_price)],
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    amount = int(payload.split("_")[1])
    
    change_balance(message.from_user.id, amount)
    new_bal = get_balance(message.from_user.id)
    
    await message.answer(
        f"✅ Оплата прошла успешно!\n"
        f"Тебе начислено {amount} тыкв 🎃\n\n"
        f"Твой новый баланс: {new_bal} тыкв."
    )

async def main():
    init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
