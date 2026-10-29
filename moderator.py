import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import config

logging.basicConfig(level=logging.INFO)

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет. Это бот-скупщик подарков.\n\n"
        "Как пользоваться:\n"
        "1. Пополни баланс бота: /buy 100 (на 100 звезд)\n"
        "2. Отправь ID подарка и количество (например: 9000000000000193 5)\n\n"
        "Бот купит указанное количество подарков и отправит их тебе."
    )

@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("Напиши количество звезд: /buy 100")
    
    amount = int(parts[1])
    if amount < 1:
        return await message.answer("Минимум 1 звезда.")

    await message.answer_invoice(
        title="Пополнение баланса бота",
        description=f"Пополнение на {amount} Stars для скупки.",
        payload=f"deposit_{amount}",
        provider_token="", 
        currency="XTR", 
        prices=[LabeledPrice(label="XTR", amount=amount)],
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    amount = int(message.successful_payment.invoice_payload.split("_")[1])
    await message.answer(f"Баланс пополнен на {amount} Stars!")

# ЛОВИМ ID И КОЛИЧЕСТВО
@dp.message(F.text.regexp(r'^\d+\s+\d+$'))
async def process_gift_order(message: Message):
    parts = message.text.split()
    gift_id = parts[0].strip()
    count = int(parts[1])
    
    if count < 1:
        return await message.answer("Количество должно быть больше 0.")
    if count > 100:
        return await message.answer("Максимум 100 штук за раз.")
    
    await message.answer(f"Начинаю скупку {count} шт. подарка с ID: {gift_id}...")
    
    success_count = 0
    for i in range(count):
        try:
            await bot.send_gift(user_id=message.from_user.id, gift_id=gift_id)
            success_count += 1
            await message.answer(f"✅ Куплен и отправлен ({i+1}/{count})")
        except Exception as e:
            await message.answer(f"❌ Ошибка на {i+1}-м подарке: {e}")
            break
        
        await asyncio.sleep(1) # Пауза, чтобы не забанили за спам
    
    await message.answer(f"Скупка завершена. Успешно куплено: {success_count} из {count}.")

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
