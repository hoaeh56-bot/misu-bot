import asyncio
import logging
import os
import random
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import psycopg2
import config

logging.basicConfig(level=logging.INFO)
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

ADMIN_ID = 1780243205 

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

# ТВОЙ ПОЛНЫЙ СПИСОК ПОДАРКОВ
GIFTS = [
    {"id": "9000000000000151", "name": "Мишка", "stars": 15},
    {"id": "9000000000000148", "name": "Сердечко", "stars": 15},
    {"id": "9000000000000152", "name": "Подарок", "stars": 25},
    {"id": "9000000000000153", "name": "Роза", "stars": 25},
    {"id": "9000000000000154", "name": "Торт", "stars": 50},
    {"id": "9000000000000155", "name": "Букет", "stars": 50},
    {"id": "9000000000000156", "name": "Ракета", "stars": 50},
    {"id": "9000000000000160", "name": "Шампанское", "stars": 50},
    {"id": "9000000000000157", "name": "Кубок", "stars": 100},
    {"id": "9000000000000158", "name": "Кольцо", "stars": 100},
    {"id": "9000000000000159", "name": "Алмаз", "stars": 100},
]

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

def get_all_users():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    con.close()
    return [row[0] for row in rows]

@dp.message(CommandStart())
async def cmd_start(message: Message):
    change_balance(message.from_user.id, 0, message.from_user.username)
    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎃 Открыть игру", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer("Привет! Жми кнопку, чтобы открыть кейсы!", reply_markup=kb)

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    bal = get_balance(message.from_user.id)
    await message.answer(f"👤 Твой ID: <code>{message.from_user.id}</code>\nБаланс: <b>{bal}</b> тыкв 🎃", parse_mode="HTML")

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    amount = int(parts[1])
    stars_price = int(amount * 5.5)
    await message.answer_invoice(
        title=f"Покупка {amount} тыкв", description=f"За {stars_price} звёзд.",
        payload=f"buy_{amount}", provider_token="", currency="XTR", 
        prices=[LabeledPrice(label="XTR", amount=stars_price)],
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    change_balance(message.from_user.id, amount)
    await message.answer(f"✅ Начислено {amount} тыкв!")

@dp.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    import json
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "withdraw":
            await bot.send_message(ADMIN_ID, f"📦 <b>Вывод!</b>\nID: <code>{data.get('user_id')}</code>\nПредмет: <b>{data.get('item_name')}</b>", parse_mode="HTML")
            await message.answer("✅ Заявка отправлена!")
    except Exception as e:
        logging.error(f"Ошибка: {e}")

# ========== АДМИНКА И ПОДАРКИ ==========
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "Выдача подарков:\n"
        "<code>/gifts all 15</code> (всем Мишку или Сердечко)\n"
        "<code>/gifts all 50</code> (всем Торт, Букет, Ракету или Шампанское)\n"
        "<code>/gifts all 100</code> (всем Кубок, Кольцо или Алмаз)\n"
        "<code>/gifts 1780243205 100</code> (одному игроку)",
        parse_mode="HTML"
    )

@dp.message(Command("gifts"))
async def cmd_gifts(message: Message):
    if message.from_user.id != ADMIN_ID: return
    
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Формат: <code>/gifts all 15</code> или <code>/gifts ID 50</code>", parse_mode="HTML")
        return

    target = parts[1]
    try:
        price_stars = int(parts[2])
    except ValueError:
        await message.answer("Сумма должна быть числом.")
        return

    # Ищем подарок за указанную цену
    suitable = [g for g in GIFTS if g["stars"] == price_stars]
    if not suitable:
        await message.answer(f"❌ Нет подарков за {price_stars} звезд. Доступные цены: 15, 25, 50, 100.")
        return
        
    gift = random.choice(suitable)

    # Рассылка
    if target.lower() == "all":
        users = get_all_users()
        if not users: return await message.answer("В базе нет игроков.")
        await message.answer(f"🎁 Раздаю подарок «{gift['name']}» ({gift['stars']}⭐) на {len(users)} игроков...")
    else:
        if not target.isdigit(): return await message.answer("Нужен ID или all.")
        users = [int(target)]
        await message.answer(f"🎁 Дарю «{gift['name']}» ({gift['stars']}⭐) игроку {target}...")

    success = 0
    for uid in users:
        try:
            # Отправляем подарок через API Мисы
            await bot.send_gift(user_id=uid, gift_id=gift["id"])
            success += 1
            await asyncio.sleep(0.15) # Пауза, чтобы не забанили за флуд
        except Exception as e:
            logging.warning(f"Не удалось подарить {uid}: {e}")
            if target.lower() != "all":
                await message.answer(f"❌ Ошибка при отправке: {e}")

    if target.lower() == "all":
        await message.answer(f"✅ Раздача завершена! Успешно: {success}/{len(users)}")
    else:
        await message.answer(f"✅ Готово!")

# === ЗАГЛУШКА ДЛЯ RENDER ===
async def handle_ping(request): return web.Response(text="OK")
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
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
