import asyncio
import logging
import os
import psycopg2
import json
import aiohttp_cors
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, 
    PreCheckoutQuery, 
    LabeledPrice, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    CallbackQuery
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import config

# НАСТРОЙКИ
logging.basicConfig(level=logging.INFO)
ADMIN_ID = 1780243396  # Твой ID

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# === СТАРТ ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    # Проверяем, есть ли реферальный чек (активация)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("check_"):
        check_id = args[1].replace("check_", "")
        await process_check_activation(message, check_id)
        return

    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Wallet", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="Создать чек", callback_data="create_check")]
    ])
    await message.answer(
        "Welcome to Crypto Bot.\n"
        "Your personal wallet has been created.\n\n"
        "Click the button below to open it.",
        reply_markup=kb
    )

# === СОЗДАНИЕ ЧЕКА ===
@dp.callback_query(F.data == "create_check")
async def ask_check_amount(callback: CallbackQuery):
    await callback.message.answer("Введите сумму чека (в USDT):")
    await callback.answer()

# Ловим текст с суммой
@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def handle_check_amount(message: Message):
    amount = float(message.text)
    if amount <= 0:
        return await message.answer("Сумма должна быть больше 0")
    
    # Проверяем баланс
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT usdt_balance FROM users WHERE user_id = %s", (message.from_user.id,))
    row = cur.fetchone()
    
    if not row or row[0] < amount:
        cur.close()
        con.close()
        return await message.answer("Недостаточно USDT на балансе.")
    
    # Списываем
    cur.execute("UPDATE users SET usdt_balance = usdt_balance - %s WHERE user_id = %s", (amount, message.from_user.id))
    con.commit()
    
    # Создаем чек без пароля
    cur.execute("INSERT INTO checks (creator_id, amount, coin, is_activated) VALUES (%s, %s, 'USDT', false) RETURNING id", (message.from_user.id, amount))
    check_id = cur.fetchone()[0]
    con.commit()
    cur.close()
    con.close()
    
    link = f"https://t.me/cryptobot?start=check_{check_id}"
    await message.answer(f"✅ Чек на {amount} USDT создан!\nСсылка: {link}")

# === АКТИВАЦИЯ ЧЕКА ===
async def process_check_activation(message: Message, check_id: str):
    con = get_db()
    cur = con.cursor()
    
    # Ищем чек
    cur.execute("SELECT amount, is_activated FROM checks WHERE id = %s", (check_id,))
    row = cur.fetchone()
    
    if not row:
        await message.answer("Чек не найден или уже активирован.")
        cur.close()
        con.close()
        return
    
    amount, is_activated = row
    
    if is_activated:
        await message.answer("Этот чек уже активирован.")
        cur.close()
        con.close()
        return
    
    # Активируем
    cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (amount, message.from_user.id))
    cur.execute("UPDATE checks SET is_activated = true, activated_by = %s WHERE id = %s", (message.from_user.id, check_id))
    con.commit()
    cur.close()
    con.close()
    
    await message.answer(f"🎉 Вы активировали чек и получили {amount} USDT на баланс!")

# === АДМИН-ПАНЕЛЬ ===
@dp.message(Command("admin_panel"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обнулить все балансы", callback_data="reset_all_balances")]
    ])
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(F.data == "reset_all_balances")
async def reset_all_balances(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE users SET usdt_balance = 0, gram_balance = 0, sol_balance = 0, trx_balance = 0")
    con.commit()
    cur.close()
    con.close()
    
    await callback.message.answer("✅ Все балансы обнулены.")
    await callback.answer()

# === ПОКУПКА КРИПТЫ ===
async def handle_buy_request(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        coin = data.get("coin")
        amount = float(data.get("amount"))
        stars = int(data.get("stars"))

        await bot.send_invoice(
            chat_id=user_id,
            title=f"Покупка {amount} {coin}",
            description=f"Оплата {stars} Stars",
            payload=f"buycrypto_{coin}_{amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=stars)],
        )
        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("buycrypto_"):
        parts = payload.split("_")
        coin = parts[1]
        amount = float(parts[2])
        user_id = message.from_user.id
        
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        
        if coin == "USDT": cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "GRAM": cur.execute("UPDATE users SET gram_balance = gram_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "SOL": cur.execute("UPDATE users SET sol_balance = sol_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "TRX": cur.execute("UPDATE users SET trx_balance = trx_balance + %s WHERE user_id = %s", (amount, user_id))
            
        con.commit()
        cur.close()
        con.close()
        await message.answer(f"✅ Успешно куплено {amount} {coin}!\nПроверь баланс в кошельке.")

# === ЗАПУСК ВЕБ-СЕРВЕРА ===
async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    app.router.add_get('/', handle_ping)
    app.router.add_post('/buy', handle_buy_request)
    
    for route in list(app.router.routes()):
        cors.add(route)
        
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"ВЕБ-СЕРВЕР ЗАПУЩЕН НА ПОРТУ {port}")

# === MAIN ===
async def main():
    asyncio.create_task(start_web_server())
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
