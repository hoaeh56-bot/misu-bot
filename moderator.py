import asyncio
import logging
import re
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
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

# Память бота: сохраняем всех, кто пишет в чат
user_cache = {}

MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False, can_send_audios=False, can_send_documents=False,
    can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
    can_send_voice_notes=False, can_send_polls=False, can_send_other_messages=False,
    can_add_web_page_previews=False,
)

UNMUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=True, can_send_audios=True, can_send_documents=True,
    can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
    can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
    can_add_web_page_previews=True,
)

async def is_chat_admin(message: Message) -> bool:
    if message.from_user.id in config.EXTRA_ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def resolve_target(message: Message):
    # 1. Пытаемся взять из Reply (на кого ответили)
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user
        
    # 2. Ищем @username или ID в тексте команды
    parts = message.text.split()
    for part in parts[1:]:
        if part.isdigit():
            try:
                member = await bot.get_chat_member(message.chat.id, int(part))
                return member.user
            except Exception:
                pass
        elif part.startswith("@"):
            username = part.replace("@", "").strip().lower()
            # Ищем в сохраненных
            if username in user_cache:
                return user_cache[username]
            try:
                member = await bot.get_chat_member(message.chat.id, f"@{username}")
                return member.user
            except Exception:
                pass
    return None

def parse_duration(arg: str):
    if not arg: return None
    matches = re.findall(r"(\d+)\s*([smhd])", arg.lower())
    if not matches: return None
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return sum(int(num) * units[unit] for num, unit in matches) or None

def fmt_duration(seconds: int) -> str:
    if seconds >= 86400: return f"{seconds // 86400}d"
    if seconds >= 3600: return f"{seconds // 3600}h"
    if seconds >= 60: return f"{seconds // 60}m"
    return f"{seconds}s"

# Запоминаем всех, кто пишет текст
@dp.message(F.text)
async def cache_users(message: Message):
    if message.from_user and message.from_user.username:
        user_cache[message.from_user.username.lower()] = message.from_user

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Бот-модератор активен.")

# ДИАГНОСТИКА: Узнаем, присылает ли MisuGram Reply
@dp.message(Command("debug"))
async def cmd_debug(message: Message):
    if not message.reply_to_message:
        await message.reply("Ты не ответил на сообщение! Сделай Reply на чье-то сообщение и напиши /debug")
        return
    
    # Выводим то, что бот видит в Reply
    info = str(message.reply_to_message)
    await message.reply(f"Данные о пользователе (Reply):\n\n<code>{info}</code>")

@dp.message(Command("mute"))
async def cmd_mute(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Только админы.")
        return
    target = await resolve_target(message)
    if not target:
        await message.reply("Не нашел юзера. Ответь на его сообщение (reply) или напиши ID/@ник.")
        return
    parts = message.text.split()
    arg = "1h"
    for part in parts[1:]:
        if not part.isdigit() and not part.startswith("@"):
            arg = part
            break
    seconds = parse_duration(arg)
    if seconds is None:
        await message.reply("Неверное время. Пример: 30m, 1h, 2d")
        return
    until = datetime.now() + timedelta(seconds=seconds)
    try:
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=target.id, permissions=MUTE_PERMISSIONS, until_date=until)
        await message.reply(f"✅ {target.full_name} замучен на {fmt_duration(seconds)}.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await is_chat_admin(message):
        await message.reply("Только админы.")
        return
    target = await resolve_target(message)
    if not target:
        await message.reply("Не нашел юзера. Ответь на его сообщение (reply) или напиши ID/@ник.")
        return
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=target.id, revoke_messages=True)
        await message.reply(f"✅ {target.full_name} забанен навсегда.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

# Остальные команды (unmute, unban) по аналогии...
@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await is_chat_admin(message): return
    target = await resolve_target(message)
    if not target: return
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=target.id)
        await message.reply("✅ Разбанен.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        pass
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
