import asyncio
import logging
import re
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ChatPermissions
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("moderator")

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

# Права на мут (запрет писать)
MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_audios=False,
    can_send_documents=False,
    can_send_photos=False,
    can_send_videos=False,
    can_send_video_notes=False,
    can_send_voice_notes=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)

# Права на размут (разрешаем всё)
UNMUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_audios=True,
    can_send_documents=True,
    can_send_photos=True,
    can_send_videos=True,
    can_send_video_notes=True,
    can_send_voice_notes=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)

async def is_chat_admin(message: Message) -> bool:
    if message.from_user.id in config.EXTRA_ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        log.warning("get_chat_member failed: %s", e)
        return False

async def get_target_id(message: Message):
    # 1. Проверяем реплай
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    # 2. Проверяем, есть ли цифры (ID) в тексте
    parts = message.text.split()
    for part in parts[1:]:
        if part.isdigit():
            return int(part)

    return None

def parse_duration(arg: str):
    if not arg:
        return None
    matches = re.findall(r"(\d+)\s*([smhd])", arg.lower())
    if not matches:
        return None
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return sum(int(num) * units[unit] for num, unit in matches) or None

def fmt_duration(seconds: int) -> str:
    if seconds >= 86400: return f"{seconds // 86400}d"
    if seconds >= 3600: return f"{seconds // 3600}h"
    if seconds >= 60: return f"{seconds // 60}m"
    return f"{seconds}s"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Бот-модератор активен.\n"
        "Использование: ответь на сообщение и напиши команду, либо напиши /ban ID"
    )

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_chat_admin(message):
        await message.reply("⛔ Только админы чата могут мутить.")
        return

    target_id = await get_target_id(message)
    if not target_id:
        await message.reply("❌ Ошибка: ответь на сообщение нарушителя (Reply) или напиши его ID цифрами.")
        return

    parts = message.text.split()
    arg = "1h"
    for part in parts[1:]:
        if not part.isdigit():
            arg = part
            break

    seconds = parse_duration(arg)
    if seconds is None:
        await message.reply("❌ Неверный формат времени. Пример: 30m, 1h, 2d")
        return

    until = datetime.now() + timedelta(seconds=seconds)
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=MUTE_PERMISSIONS,
            until_date=until,
        )
        await message.reply(f"✅ Пользователь замучен на {fmt_duration(seconds)}.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_chat_admin(message):
        await message.reply("⛔ Только админы чата могут банить.")
        return

    target_id = await get_target_id(message)
    if not target_id:
        await message.reply("❌ Ошибка: ответь на сообщение нарушителя (Reply) или напиши его ID цифрами.")
        return

    try:
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            revoke_messages=True,
        )
        await message.reply(f"✅ Пользователь забанен навсегда.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_chat_admin(message): return
    target_id = await get_target_id(message)
    if not target_id: return await message.reply("❌ Ответь или напиши ID.")
    
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
            permissions=UNMUTE_PERMISSIONS,
        )
        await message.reply(f"✅ Мут снят.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_chat_admin(message): return
    target_id = await get_target_id(message)
    if not target_id: return await message.reply("❌ Ответь или напиши ID.")

    try:
        await bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target_id,
        )
        await message.reply(f"✅ Пользователь разбанен.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
