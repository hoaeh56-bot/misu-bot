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

# ТВОЙ ID ДЛЯ ПОЛУЧЕНИЯ ЗАЯВОК НА ВЫВОД
ADMIN_ID = 1780243205 

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0)")
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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    change_balance(message.from_user.id, 0, message.from_user.username)
    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
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
    await message.answer(f"👤 Твой ID: <code>{user_id}</code>\nБаланс: <b>{bal}</b> тыкв 🎃", parse_mode="HTML")

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
    await message.answer(f"✅ Оплата прошла успешно!\nТебе начислено {amount} тыкв 🎃\n\nТвой новый баланс: {new_bal} тыкв.")

# ЛОВИМ ДАННЫЕ ОТ САЙТА (ВЫВОД ПРЕДМЕТОВ)
@dp.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    import json
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "withdraw":
            item_name = data.get("item_name")
            user_id = data.get("user_id")
            
            # Отправляем тебе уведомление
            await bot.send_message(
                ADMIN_ID,
                f"📦 <b>Запрос на вывод!</b>\n\n"
                f"Игрок (ID): <code>{user_id}</code>\n"
                f"Предмет: <b>{item_name}</b>\n\n"
                f"Свяжись с ним для выдачи.",
                parse_mode="HTML"
            )
            await message.answer("✅ Запрос на вывод отправлен администратору!")
    except Exception as e:
        logging.error(f"Ошибка обработки web_app_data: {e}")

async def main():
    init_db()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except:
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
