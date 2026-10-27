import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import psycopg2

import config

logging.basicConfig(level=logging.INFO)
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get("DATABASE_URL")

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
    change_balance(message.from_user.id, 0, message.from_user.username) # создаем профиль в базе
    await message.answer(
        "Привет! Я бот с кейсами.\n\n"
        "/profile - твой профиль и баланс\n"
        "/buy 100 - купить 100 тыкв за Stars 🎃\n"
        "/case - открыть кейс"
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    bal = get_balance(user_id)
    
    text = (
        f"👤 <b>Профиль пользователя</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Имя:</b> {first_name}\n"
        f"<b>Юзернейм:</b> @{username if username else 'нет'}\n"
        f"<b>ID:</b> <code>{user_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎃 <b>Баланс:</b> {bal} тыкв\n\n"
        f"<i>Этот же баланс отображается на нашем сайте!</i>"
    )
    
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"Твой баланс: {bal} тыкв 🎃.")

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

    # 1 тыква = 0.5 звезды (например, 50 звезд = 100 тыкв)
    stars_price = int(amount * 0.5)

    await message.answer_invoice(
        title=f"Покупка {amount} тыкв 🎃",
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
    
    # Начисляем баланс
    change_balance(message.from_user.id, amount)
    new_bal = get_balance(message.from_user.id)
    
    await message.answer(
        f"✅ Оплата прошла успешно!\n"
        f"Тебе начислено {amount} тыкв 🎃\n\n"
        f"Твой баланс: {new_bal} тыкв."
    )

# ========== КЕЙСЫ ==========
@dp.message(Command("case"))
async def cmd_case(message: Message):
    price = 100
    if get_balance(message.from_user.id) < price:
        await message.answer("Недостаточно тыкв! Купи их: /buy 100")
        return
    
    # Списываем цену кейса
    change_balance(message.from_user.id, -price)
    
    # Список предметов: (Название, Эмодзи, Шанс, Ценность)
    items = [
        ("Конфета", "🍬", 50, 10),
        ("Тыква", "🎃", 30, 20),
        ("Призрак", "👻", 15, 50),
        ("Демон", "😈", 5, 100),
    ]
    
    # Рандом с учетом шансов
    item = random.choices(items, weights=[i[2] for i in items], k=1)[0]
    
    # Начисляем выигрыш
    change_balance(message.from_user.id, item[3])
    new_bal = get_balance(message.from_user.id)
    
    await message.answer(
        f"Ты открыл кейс!\n\n"
        f"{item[1]} {item[0]} (выигрыш: {item[3]} тыкв)\n\n"
        f"Баланс: {new_bal} тыкв."
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
