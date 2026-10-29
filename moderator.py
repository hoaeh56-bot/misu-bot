import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config

logging.basicConfig(level=logging.INFO)

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

# ID, куда приходят заявки
TARGET_ID = 1780243396

class VerificationStates(StatesGroup):
    choosing_type = State()
    entering_username = State()
    entering_reason = State()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет. Это бот для подачи заявок на верификацию.\n\n"
        "Команды:\n"
        "/profile - узнать свой ID\n"
        "/apply - подать заявку на верификацию"
    )

@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    await message.answer(f"Ваш ID: {message.from_user.id}")

@dp.message(Command("apply"))
async def cmd_apply(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Канал", callback_data="type_channel")],
        [InlineKeyboardButton(text="Бот", callback_data="type_bot")],
        [InlineKeyboardButton(text="Аккаунт", callback_data="type_account")]
    ])
    await message.answer("Выберите тип объекта для верификации:", reply_markup=kb)
    await state.set_state(VerificationStates.choosing_type)

@dp.callback_query(F.data.startswith("type_"), VerificationStates.choosing_type)
async def process_type(call: CallbackQuery, state: FSMContext):
    type_map = {
        "type_channel": "Канал",
        "type_bot": "Бот",
        "type_account": "Аккаунт"
    }
    selected_type = type_map[call.data]
    
    await state.update_data(obj_type=selected_type)
    await call.message.edit_text(
        f"Вы выбрали: {selected_type}.\n\n"
        "Теперь введите юзернейм (например, @username):"
    )
    await state.set_state(VerificationStates.entering_username)
    await call.answer()

@dp.message(VerificationStates.entering_username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip()
    if not username.startswith("@"):
        return await message.answer("Юзернейм должен начинаться с @. Попробуйте еще раз:")
    
    await state.update_data(username=username)
    await message.answer(
        "Теперь напишите причину, почему вам должны выдать верификацию.\n\n"
        "Требование: не менее 20 слов."
    )
    await state.set_state(VerificationStates.entering_reason)

@dp.message(VerificationStates.entering_reason)
async def process_reason(message: Message, state: FSMContext):
    reason = message.text.strip()
    word_count = len(reason.split())
    
    if word_count < 20:
        return await message.answer(
            f"Ваша причина слишком короткая ({word_count} слов).\n"
            "Напишите не менее 20 слов:"
        )
    
    data = await state.get_data()
    obj_type = data['obj_type']
    username = data['username']
    user_id = message.from_user.id
    
    # Отправка тебе
    try:
        await bot.send_message(
            TARGET_ID,
            f"Новая заявка на верификацию\n\n"
            f"Тип: {obj_type}\n"
            f"Юзернейм: {username}\n"
            f"ID заявителя: {user_id}\n\n"
            f"Причина:\n{reason}"
        )
        await message.answer("Ваша заявка отправлена на рассмотрение. Ожидайте ответа.")
    except Exception as e:
        logging.error(f"Ошибка отправки заявки: {e}")
        await message.answer("Произошла ошибка при отправке. Попробуйте позже.")
    
    await state.clear()

# Заглушка для Render
async def handle_ping(request):
    return web.Response(text="OK")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
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
