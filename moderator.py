import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
import os
import config

logging.basicConfig(level=logging.INFO)

# 1. СОЗДАЕМ БОТА И ДИСПЕТЧЕР (В САМОМ НАЧАЛЕ)
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

# 2. ТВОЙ ID (АДМИН)
ADMIN_ID = 1780243205

# 3. КОМАНДЫ
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Я бот-верификатор компании Corporate Freezers.\n\n"
        "Чтобы выдать метку, напиши:\n"
        "/verify @юзернейм"
    )

@dp.message(Command("verify"))
async def cmd_verify(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ У тебя нет прав для этой команды.")
    
    parts = message.text.split()
    if len(parts) < 2:
        return await message.answer("Использование: /verify @юзернейм")
    
    target = parts[1]
    if not target.startswith("@"):
        return await message.answer("Юзернейм должен начинаться с @")
    
    try:
        # Пытаемся выдать метку через API
        await bot.session.make_request(
            method="setCustomVerification",
            data={
                "enabled": True,
                "peer": target, 
                "custom_description": "Проверено Corporate Freezers"
            }
        )
        await message.answer(f"✅ Метка выдана для {target}")
    except Exception as e:
        await message.answer(f"❌ Ошибка API: {e}")

# 4. ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не падал)
async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 10000)))
    await site.start()
    logging.info("ВЕБ-СЕРВЕР ЗАПУЩЕН")

# 5. ЗАПУСК
async def main():
    asyncio.create_task(start_web_server())
    try: 
        await bot.delete_webhook(drop_pending_updates=True)
    except: 
        pass
    logging.info("БОТ ЗАПУЩЕН")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
