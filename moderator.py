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

class AdminStates(StatesGroup):
    waiting_for_id = State()
    waiting_for_amount = State()
    waiting_for_gift_price = State()

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

def get_all_users():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    con.close()
    return [row[0] for row in rows]

async def check_withdrawals():
    while True:
        try:
            con = get_db()
            cur = con.cursor()
            cur.execute("SELECT id, user_id, item_name FROM withdrawals WHERE status = 'pending' LIMIT 1")
            row = cur.fetchone()
            
            if row:
                w_id, u_id, item_name = row
                await bot.send_message(
                    ADMIN_ID,
                    f"📦 <b>ЗАЯВКА НА ВЫВОД!</b>\n\nИгрок (ID): <code>{u_id}</code>\nПредмет: <b>{item_name}</b>",
                    parse_mode="HTML"
                )
                cur.execute("UPDATE withdrawals SET status = 'done' WHERE id = %s", (w_id,))
                con.commit()
            cur.close()
            con.close()
        except Exception as e:
            logging.error(f"Ошибка: {e}")
        await asyncio.sleep(5)

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

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать / Забрать тыквы", callback_data="admin_give")],
        [InlineKeyboardButton(text="🎁 Выдать подарок всем", callback_data="admin_gift")]
    ])
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "admin_give")
async def admin_give_callback(call: Message, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("Введи <b>ID игрока</b>:")
    await state.set_state(AdminStates.waiting_for_id)

@dp.message(AdminStates.waiting_for_id)
async def admin_process_id(message: Message, state: FSMContext):
    if not message.text.isdigit(): return await message.answer("Только цифры.")
    await state.update_data(target_id=int(message.text))
    await state.set_state(AdminStates.waiting_for_amount)
    await message.answer("Сколько <b>тыкв</b>? (Минус, чтобы забрать)")

@dp.message(AdminStates.waiting_for_amount)
async def admin_process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError: return await message.answer("Нужно число.")
    data = await state.get_data()
    target_id = data['target_id']
    change_balance(target_id, amount)
    new_bal = get_balance(target_id)
    await state.clear()
    await message.answer(f"✅ Баланс <code>{target_id}</code> изменен на <b>{amount}</b> 🎃\nЕго баланс: <b>{new_bal}</b>", parse_mode="HTML")

@dp.callback_query(F.data == "admin_gift")
async def admin_gift_callback(call: Message, state: FSMContext):
    if call.from_user.id != ADMIN_ID: return
    await call.message.edit_text("Сколько <b>звезд</b> должен стоить подарок? (15, 25, 50, 100)")
    await state.set_state(AdminStates.waiting_for_gift_price)

@dp.message(AdminStates.waiting_for_gift_price)
async def admin_process_gift_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError: return await message.answer("Нужно число.")
    suitable = [g for g in GIFTS if g["stars"] == price]
    if not suitable: 
        await state.clear()
        return await message.answer("Нет подарка за такую цену.")
    gift = random.choice(suitable)
    users = get_all_users()
    if not users:
        await state.clear()
        return await message.answer("Нет игроков.")
    await message.answer(f"🎁 Раздаю «{gift['name']}» на {len(users)} игроков...")
    success = 0
    for uid in users:
        try:
            await bot.send_gift(user_id=uid, gift_id=gift["id"])
            success += 1
            await asyncio.sleep(0.15)
        except Exception as e:
            pass
    await state.clear()
    await message.answer(f"✅ Успешно: {success}/{len(users)}")

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit(): return
    amount = int(parts[1])
    stars_price = int(amount * 5.5)
    await message.answer_invoice(title=f"Покупка {amount} тыкв", description=f"За {stars_price} звёзд.", payload=f"buy_{amount}", provider_token="", currency="XTR", prices=[LabeledPrice(label="XTR", amount=stars_price)])

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    change_balance(message.from_user.id, amount)
    await message.answer(f"✅ Начислено {amount} тыкв!")

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
    asyncio.create_task(check_withdrawals())
    try: await bot.delete_webhook(drop_pending_updates=True)
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
