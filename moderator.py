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

# ИЗМЕНЕНИЕ 1: Проверка админа теперь работает в любом чате
async def is_chat_admin(message: Message) -> bool:
    # Твой личный ID (из config.py) всегда имеет доступ
    if message.from_user.id in config.EXTRA_ADMIN_IDS:
        return True
        
    # Проверяем, является ли человек админом именно в ЭТОМ чате
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        log.warning("get_chat_member failed: %s", e)
        return False

def get_target(message: Message):
    if not message.reply_to_message:
        return None
    return message.reply_to_message.from_user

def parse_duration(arg: str):
    if not arg:
        return None
    matches = re.findall(r"(\d+)\s*([smhd])", arg.lower())
    if not matches:
        return None
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    total = 0
    for num, unit in matches:
        total += int(num) * units[unit]
    return total if total > 0 else None

def fmt_duration(seconds: int) -> str:
    if seconds >= 86400:
        return f"{seconds // 86400}d"
    if seconds >= 3600:
        return f"{seconds // 3600}h"
    if seconds >= 60:
        return f"{seconds // 60}m"
    return f"{seconds}s"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Bot-moderator\n\n"
        "Commands (chat admins only):\n"
        "/chatid - show chat id\n"
        "/mute 1h - mute (reply to a message)\n"
        "/ban - ban forever (reply)\n"
        "/unmute - remove mute (reply)\n"
        "/unban - unban (reply)\n\n"
        "Time: 30m, 1h, 2d, 1h30m"
    )

@dp.message(Command("chatid"))
async def cmd_chatid(message: Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Only chat admins can mute.")
        return

    target = get_target(message)
    if not target:
        await message.reply("Reply to a user's message with this command.")
        return

    parts = message.text.split(maxsplit=1)
    arg = parts[1].strip() if len(parts) > 1 else "1h"
    seconds = parse_duration(arg)
    if seconds is None:
        await message.reply("Bad duration. Examples: 30m, 1h, 2d, 1h30m")
        return

    until = datetime.now() + timedelta(seconds=seconds)

    try:
        # ИЗМЕНЕНИЕ 2: Мут применяется в текущем чате
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=MUTE_PERMISSIONS,
            until_date=until,
        )
        await message.reply(f"{target.full_name} muted for {fmt_duration(seconds)}.")
    except Exception as e:
        log.error("mute failed: %s", e)
        await message.reply(f"Error: {e}")

@dp.message(Command("unmute"))
async def cmd_unmute(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Only chat admins.")
        return

    target = get_target(message)
    if not target:
        await message.reply("Reply to a user's message.")
        return

    try:
        # ИЗМЕНЕНИЕ 3: Размут применяется в текущем чате
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=UNMUTE_PERMISSIONS,
        )
        await message.reply(f"{target.full_name} unmuted.")
    except Exception as e:
        log.error("unmute failed: %s", e)
        await message.reply(f"Error: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Only chat admins can ban.")
        return

    target = get_target(message)
    if not target:
        await message.reply("Reply to a user's message with this command.")
        return

    try:
        # ИЗМЕНЕНИЕ 4: Бан применяется в текущем чате
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            revoke_messages=True,
        )
        await message.reply(f"{target.full_name} banned forever.")
    except Exception as e:
        log.error("ban failed: %s", e)
        await message.reply(f"Error: {e}")

@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Only chat admins.")
        return

    target = get_target(message)
    if not target:
        await message.reply("Reply to a user's message.")
        return

    try:
        # ИЗМЕНЕНИЕ 5: Разбан применяется в текущем чате
        await bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
        )
        await message.reply(f"{target.full_name} unbanned.")
    except Exception as e:
        log.error("unban failed: %s", e)
        await message.reply(f"Error: {e}")

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        log.warning("delete_webhook failed: %s", e)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
