import asyncio
import logging
import os
import random
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

# Список подарков
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
    {"id": "9000000000000193", "name": "Фламинго (Pool Float)", "stars": 150},
]

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Бот-автоскупщик подарков.\n\n"
        "1. Пополни баланс: /buy 100\n"
        "2. Запусти скупку: /autobuy 5 (где 5 — количество штук)\n\n"
        "Бот будет покупать подарки и отправлять их тебе."
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
        description=f"Пополнение на {amount} Stars для автоскупа.",
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

@dp.message(Command("autobuy"))
async def cmd_autobuy(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        return await message.answer("Напиши: /autobuy 5 (где 5 — количество штук)")
    
    count = int(parts[1])
    if count < 1:
        return await message.answer("Количество должно быть больше 0.")
    
    await message.answer(f"Запущен автоскуп на {count} штук. Начинаю...")
    
    await perform_autobuy(message.chat.id, message.from_user.id, count)

async def perform_autobuy(chat_id, user_id, count):
    # Берем случайный подарок из списка для каждого покупателя
    gift = random.choice(GIFTS)
    
    success_count = 0
    for i in range(count):
        try:
            # Отправляем подарок тому, кто запустил
            await bot.send_gift(user_id=user_id, gift_id=gift["id"])
            success_count += 1
            await bot.send_message(chat_id, f"✅ Куплен и отправлен: {gift['name']} ({i+1}/{count})")
        except Exception as e:
            await bot.send_message(chat_id, f"❌ Ошибка при покупке: {e}")
            break
        
        await asyncio.sleep(1)
    
    await bot.send_message(chat_id, f"Автоскуп завершен. Успешно куплено: {success_count} шт.")

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
