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

class AdminStates(StatesGroup):
    waiting_for_id = State()
    waiting_for_amount = State()

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

# === ПРОВЕРКА ЗАЯВОК НА ВЫВОД ===
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
                    f"📦 <b>ЗАЯВКА НА ВЫВОД!</b>\n\n"
                    f"Игрок (ID): <code>{u_id}</code>\n"
                    f"Предмет: <b>{item_name}</b>",
                    parse_mode="HTML"
                )
                cur.execute("UPDATE withdrawals SET status = 'done' WHERE id = %s", (w_id,))
                con.commit()
            
            cur.close()
            con.close()
        except Exception as e:
            logging.error(f"Ошибка проверки заявок: {e}")
        
        await asyncio.sleep(5)

# === КОМАНДЫ ===
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

# === АДМИН ПАНЕЛЬ ===
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать / Забрать тыквы", callback_data="admin_give")]
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
    await message.answer("Сколько <b>тыкв</b> выдать? (Чтобы забрать, напиши с минусом, например: -500)")

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
    await message.answer(f"✅ Игроку <code>{target_id}</code> изменен баланс на <b>{amount}</b> 🎃\nЕго баланс: <b>{new_bal}</b> 🎃", parse_mode="HTML")

# Покупка и прочее
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
