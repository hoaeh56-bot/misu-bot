import asyncio
import logging
import os
import psycopg2
import aiohttp_cors
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup,
    InlineKeyboardButton, WebAppInfo, CallbackQuery, FSInputFile
)
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from PIL import Image, ImageDraw, ImageFont
import config

logging.basicConfig(level=logging.INFO)
ADMIN_ID = 1780243396

session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://...")

def get_db():
    return psycopg2.connect(DATABASE_URL)

# === ГЕНЕРАЦИЯ КАРТИНКИ ЧЕКА ===
def generate_check_image(amount, coin):
    # Создаем картинку 800x400 с градиентом
    width, height = 800, 400
    img = Image.new('RGB', (width, height), color='#1e1e1e')
    draw = ImageDraw.Draw(img)

    # Градиент (от синего к фиолетовому)
    for y in range(height):
        r = int(25 + (100 - 25) * (y / height))
        g = int(118 + (50 - 118) * (y / height))
        b = int(210 + (200 - 210) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Пытаемся загрузить шрифт (стандартный для Linux на Render)
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        # Если шрифт не найден, используем стандартный
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Рисуем сумму
    amount_text = f"{amount} {coin}"
    # Центрируем текст
    bbox = draw.textbbox((0, 0), amount_text, font=font_large)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((width - text_w) / 2, (height - text_h) / 2 - 20), amount_text, font=font_large, fill="white")

    # Рисуем подпись
    subtitle = "Crypto Check"
    bbox_sub = draw.textbbox((0, 0), subtitle, font=font_small)
    sub_w = bbox_sub[2] - bbox_sub[0]
    draw.text(((width - sub_w) / 2, (height / 2) + 80), subtitle, font=font_small, fill="#dddddd")

    # Сохраняем
    filepath = f"check_{amount}_{coin}.png"
    img.save(filepath)
    return filepath

# === СТАРТ ===
@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("check_"):
        check_id = args[1].replace("check_", "")
        await process_check_activation(message, check_id)
        return

    web_app_url = f"https://misu-site.vercel.app/?user_id={message.from_user.id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Wallet", web_app=WebAppInfo(url=web_app_url))],
        [InlineKeyboardButton(text="Создать чек", callback_data="create_check")]
    ])
    await message.answer(
        "Welcome to Crypto Bot.\nYour wallet is ready. Click below to open it.",
        reply_markup=kb
    )

# === СОЗДАНИЕ ЧЕКА ===
@dp.callback_query(F.data == "create_check")
async def ask_check_amount(callback: CallbackQuery):
    await callback.message.answer("Введите сумму чека (в USDT):")
    await callback.answer()

@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def handle_check_amount(message: Message):
    amount = float(message.text)
    if amount <= 0:
        return await message.answer("Сумма должна быть больше 0")
    
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT usdt_balance FROM users WHERE user_id = %s", (message.from_user.id,))
    row = cur.fetchone()
    
    if not row or row[0] < amount:
        cur.close()
        con.close()
        return await message.answer("Недостаточно USDT на балансе.")
    
    cur.execute("UPDATE users SET usdt_balance = usdt_balance - %s WHERE user_id = %s", (amount, message.from_user.id))
    con.commit()
    
    cur.execute("INSERT INTO checks (creator_id, amount, coin, is_activated) VALUES (%s, %s, 'USDT', false) RETURNING id", (message.from_user.id, amount))
    check_id = cur.fetchone()[0]
    con.commit()
    cur.close()
    con.close()

    # Генерируем картинку
    img_path = generate_check_image(amount, "USDT")

    caption = (
        f"🎁 **Чек на {amount} USDT**\n\n"
        f"Чтобы активировать, нажмите кнопку ниже."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Получить {amount} USDT", url=f"https://t.me/cryptobot?start=check_{check_id}")]
    ])
    
    # Отправляем фото с кнопкой
    photo = FSInputFile(img_path)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        reply_markup=kb,
        parse_mode="Markdown"
    )

    # Удаляем временный файл
    os.remove(img_path)

# === АКТИВАЦИЯ ЧЕКА ===
async def process_check_activation(message: Message, check_id: str):
    con = get_db()
    cur = con.cursor()
    
    cur.execute("SELECT amount, is_activated FROM checks WHERE id = %s", (check_id,))
    row = cur.fetchone()
    
    if not row:
        await message.answer("Чек не найден.")
        cur.close(); con.close()
        return
    
    amount, is_activated = row
    
    if is_activated:
        await message.answer("Этот чек уже активирован.")
        cur.close(); con.close()
        return
    
    cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (amount, message.from_user.id))
    cur.execute("UPDATE checks SET is_activated = true, activated_by = %s WHERE id = %s", (message.from_user.id, check_id))
    con.commit()
    cur.close()
    con.close()
    
    await message.answer(f"🎉 Вы активировали чек и получили {amount} USDT!")

# (ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ: АДМИНКА, ВЕБ-СЕРВЕР, ОПЛАТА)
# ...
