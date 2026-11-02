import aiosqlite
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

router = Router()
DB_PATH = "celestiana_bot.db"

# --- КОМАНДА .мойпол ---
@router.message(Command("мойпол"))
async def set_gender(message: Message, command: CommandObject):
    if not command.args or command.args.lower() not in ['м', 'ж']:
        await message.reply("⚠️ Укажи пол: .мойпол м или .мойпол ж")
        return
    
    gender = command.args.lower()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET gender = ? WHERE user_id = ?", 
            (gender, message.from_user.id)
        )
        # Если юзера еще нет в базе (не нажимал /start)
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, gender) VALUES (?, ?, ?)",
            (message.from_user.id, message.from_user.username, gender)
        )
        await db.commit()
    
    await message.reply(f"✅ Твой пол установлен: {'Мужской' if gender == 'м' else 'Женский'}. Теперь команды отношений доступны.")

# --- КОМАНДА .отн запрос ---
@router.message(Command("отн"))
async def relationship_handler(message: Message, command: CommandObject):
    if not command.args:
        return
        
    args = command.args.split()
    action = args[0].lower()

    if action == "запрос":
        if not message.reply_to_message:
            await message.reply("💔 Ответь на сообщение человека, с которым хочешь начать отношения.")
            return
        
        target_id = message.reply_to_message.from_user.id
        target_name = message.reply_to_message.from_user.first_name
        initiator_id = message.from_user.id
        initiator_name = message.from_user.first_name
        
        if target_id == initiator_id:
            await message.reply("🤨 Нельзя вступить в отношения с самим собой.")
            return

        # Проверка в БД: свободны ли оба в этом чате
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT * FROM couples WHERE chat_id = ? AND status = 'ACTIVE' AND (user1_id = ? OR user2_id = ? OR user1_id = ? OR user2_id = ?)",
                (message.chat.id, initiator_id, initiator_id, target_id, target_id)
            ) as cursor:
                if await cursor.fetchone():
                    await message.reply("❌ Один из вас уже состоит в отношениях в этом чате.")
                    return

        # Кнопка согласия
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data=f"accept_rel_{initiator_id}_{target_id}"),
             InlineKeyboardButton(text="❌ Нет", callback_data="decline_rel")]
        ])
        
        await message.reply(
            f"💖 <b>{target_name}</b>, минутку внимания!\n"
            f"<b>{initiator_name}</b> предлагает тебе начать отношения.\n"
            f"У тебя есть 2 минуты, чтобы ответить.",
            reply_markup=kb
        )

# --- ОБРАБОТКА КНОПКИ "ДА" ---
@router.callback_query(F.data.startswith("accept_rel_"))
async def process_accept(callback: CallbackQuery):
    data = callback.data.split("_")
    initiator_id = int(data[2])
    target_id = int(data[3])
    
    # Записываем пару в БД
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO couples (chat_id, user1_id, user2_id, sparks, level) VALUES (?, ?, ?, 100, 1)",
            (callback.message.chat.id, initiator_id, target_id)
        )
        await db.commit()
        
    await callback.message.edit_text(
        f"💖 Отношения заключены!\n"
        f"Пара получает <b>100 искр</b> и свидетельство о заключении отношений.\n"
        f"Напишите `.отн я`, чтобы посмотреть профиль."
    )
    await callback.answer("Отношения созданы!")

# --- ОБРАБОТКА КНОПКИ "НЕТ" ---
@router.callback_query(F.data == "decline_rel")
async def process_decline(callback: CallbackQuery):
    await callback.message.edit_text("💔 Предложение отклонено.")
    await callback.answer()
