import asyncio
import logging
import os
import psycopg2
import json
import aiohttp_cors
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import config

logging.basicConfig(level=logging.INFO)

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Wallet", web_app=WebAppInfo(url=web_app_url))]
    ])
    await message.answer(
        "Welcome to Crypto Bot.\n"
        "Your personal wallet has been created.\n\n"
        "Click the button below to open it.",
        reply_markup=kb
    )

# === ПРИЕМ ЗАПРОСОВ С САЙТА ===
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

# === ЗАПУСК ВЕБ-СЕРВЕРА С CORS ===
async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    
    # РАЗРЕШАЕМ ЗАПРОСЫ С САЙТА
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
    
    # Применяем CORS
    for route in list(app.router.routes()):
        cors.add(route)
        
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"ВЕБ-СЕРВЕР ЗАПУЩЕН НА ПОРТУ {port}")

async def main():
    asyncio.create_task(start_web_server())
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
@dp.message(Command("test_gifts"))
async def cmd_test_gifts(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        # Пробуем запросить доступные подарки
        result = await bot.get_available_gifts()
        await message.answer(f"✅ Сервер вернул данные:\n{result}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при запросе подарков:\n<code>{e}</code>", parse_mode="HTML")
