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


async def is_chat_admin(message: Message) -> bool:
    # Если это ты (твой ID из config.py), доступ разрешен всегда
    if message.from_user.id in config.EXTRA_ADMIN_IDS:
        return True
    # Иначе проверяем, являешься ли ты админом именно в этом чате
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception as e:
        log.warning("get_chat_member failed: %s", e)
        return False


async def resolve_target(message: Message):
    # 1. Если ответили реплаем
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
        
    # 2. Если написали ID или @username в тексте
    parts = message.text.split()
    for part in parts[1:]:
        if part.isdigit():
            try:
                member = await bot.get_chat_member(message.chat.id, int(part))
                return member.user
            except Exception:
                pass
        elif part.startswith("@"):
            username = part.replace("@", "").strip()
            try:
                member = await bot.get_chat_member(message.chat.id, f"@{username}")
                return member.user
            except Exception:
                pass
                
    return None


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
        "/mute 1h (reply) - mute\n"
        "/mute 12345678 1h (by ID) - mute\n"
        "/mute @user 1h (by @) - mute\n"
        "/ban (reply or ID or @) - ban forever\n"
        "/unmute, /unban\n\n"
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

    target = await resolve_target(message)
    if not target:
        await message.reply("Reply to a user, OR write user ID (123456), OR write @username.\nExample: /mute 1h")
        return

    # Ищем время в тексте, пропуская ID и @username
    parts = message.text.split()
    arg = "1h" # время по умолчанию
    for part in parts[1:]:
        if not part.isdigit() and not part.startswith("@"):
            arg = part
            break

    seconds = parse_duration(arg)
    if seconds is None:
        await message.reply("Bad duration. Examples: 30m, 1h, 2d, 1h30m")
        return

    until = datetime.now() + timedelta(seconds=seconds)

    try:
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

    target = await resolve_target(message)
    if not target:
        await message.reply("Reply to a user, OR write user ID (123456), OR write @username.")
        return

    try:
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

    target = await resolve_target(message)
    if not target:
        await message.reply("Reply to a user, OR write user ID (123456), OR write @username.")
        return

    try:
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

    target = await resolve_target(message)
    if not target:
        await message.reply("Reply to a user, OR write user ID (123456), OR write @username.")
        return

    try:
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
