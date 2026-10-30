import asyncio
import logging
import os
import json
import psycopg2
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

# ЛОВИМ ЗАПРОС ОТ БИРЖИ
@dp.message(F.web_app_data)
async def web_app_data_handler(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get("action") == "buy_crypto":
            coin = data.get("coin")
            amount = float(data.get("amount"))
            stars = int(data.get("stars"))
            
            # Сохраняем в payload, чтобы при оплате знать, что зачислить
            payload = f"buycrypto_{coin}_{amount}"
            
            await message.answer_invoice(
                title=f"Покупка {amount} {coin}",
                description=f"Оплата {stars} Stars",
                payload=payload,
                provider_token="", 
                currency="XTR", 
                prices=[LabeledPrice(label="XTR", amount=stars)],
            )
    except Exception as e:
        logging.error(f"Ошибка web_app_data: {e}")

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
        
        # Зачисляем в базу
        con = get_db()
        cur = con.cursor()
        
        # Проверяем, есть ли юзер
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        
        # Обновляем нужную колонку
        if coin == "USDT":
            cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "GRAM":
            cur.execute("UPDATE users SET gram_balance = gram_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "SOL":
            cur.execute("UPDATE users SET sol_balance = sol_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "TRX":
            cur.execute("UPDATE users SET trx_balance = trx_balance + %s WHERE user_id = %s", (amount, user_id))
            
        con.commit()
        cur.close()
        con.close()
        
        await message.answer(f"✅ Успешно куплено {amount} {coin}!\nПроверь баланс в кошельке.")

async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()

async def main():
    asyncio.create_task(start_web_server())
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
