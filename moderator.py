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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

ADMIN_ID = 1780243396  # Твой ID

# Подключение к кастомному серверу Missgram
session = AiohttpSession(api=TelegramAPIServer.from_base(config.API_SERVER))
bot = Bot(token=config.TOKEN, session=session)
dp = Dispatcher()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://postgres.ptcofqwsvyytcnoerazu:22E%23bS%23aMcN%40L6A@aws-0-eu-north-1.pooler.supabase.com:5432/postgres"
)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ==========================================
# ГЕНЕРАЦИЯ КАРТИНКИ ЧЕКА (С ИКОНКАМИ)
# ==========================================
def generate_check_image(amount, coin):
    width, height = 800, 400
    img = Image.new('RGB', (width, height), color='#1e1e1e')
    draw = ImageDraw.Draw(img)

    # Цвета для градиента в зависимости от валюты
    colors = {
        'USDT': (38, 161, 123),   # Зеленый
        'GRAM': (0, 136, 204),    # Синий
        'SOL':  (153, 69, 255),   # Фиолетовый
        'TRX':  (255, 0, 0)       # Красный
    }
    base_color = colors.get(coin, (25, 118, 210))

    # Рисуем градиент (от темного к цветному)
    for y in range(height):
        r = int(base_color[0] * (0.2 + 0.8 * (y / height)))
        g = int(base_color[1] * (0.2 + 0.8 * (y / height)))
        b = int(base_color[2] * (0.2 + 0.8 * (y / height)))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Загружаем шрифты
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 110)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        font_icon = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_icon = ImageFont.load_default()

    # Иконка валюты (слева)
    icon_size = 120
    icon_x = 80
    icon_y = (height - icon_size) // 2

    icon_path = f"{coin.lower()}.png"
    try:
        # Пытаемся загрузить PNG, если есть
        icon = Image.open(icon_path).convert("RGBA")
        icon = icon.resize((icon_size, icon_size))
        img.paste(icon, (icon_x, icon_y), icon)
    except:
        # Если PNG нет, рисуем белый кружок с буквой
        draw.ellipse((icon_x, icon_y, icon_x + icon_size, icon_y + icon_size), fill="white")
        letter = coin[0]
        bbox = draw.textbbox((0, 0), letter, font=font_icon)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text((icon_x + (icon_size - w) / 2, icon_y + (icon_size - h) / 2 - 15), letter, font=font_icon, fill=base_color)

    # Сумма (справа от иконки)
    amount_text = f"{amount}"
    draw.text((240, height // 2 - 80), amount_text, font=font_large, fill="white")
    
    # Название валюты (под суммой)
    draw.text((250, height // 2 + 40), coin, font=font_small, fill="#eeeeee")
    
    # Подпись внизу
    draw.text((80, height - 60), "Crypto Check", font=font_small, fill="#cccccc")

    filepath = f"check_{amount}_{coin}.png"
    img.save(filepath)
    return filepath

# ==========================================
# СТАРТ
# ==========================================
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
        "Welcome to Crypto Bot.\nYour wallet is ready. Click below to open it.\n\n"
        "Доступные команды:\n"
        "/send 100 USDT - создать чек\n"
        "/balance - посмотреть баланс\n"
        "/invoice 50 - создать счет на оплату",
        reply_markup=kb
    )

# ==========================================
# СОЗДАНИЕ ЧЕКА (Кнопка)
# ==========================================
@dp.callback_query(F.data == "create_check")
async def ask_check_amount(callback: CallbackQuery):
    await callback.message.answer("Введите сумму и валюту через пробел (например: 100 USDT):")
    await callback.answer()

# Ловим сумму для чека (если написали просто "100")
@dp.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def handle_check_amount(message: Message):
    amount = float(message.text)
    await create_check_logic(message, amount, 'USDT')

# ==========================================
# КОМАНДА /send
# ==========================================
@dp.message(Command("send"))
async def cmd_send_check(message: Message):
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Использование: /send 100 USDT\nВалюты: USDT, GRAM, SOL, TRX")
    
    try:
        amount = float(args[1])
        coin = args[2].upper()
        if coin not in ['USDT', 'GRAM', 'SOL', 'TRX']:
            return await message.answer("Неверная валюта. Доступны: USDT, GRAM, SOL, TRX")
    except:
        return await message.answer("Ошибка. Пример: /send 100 USDT")
    
    await create_check_logic(message, amount, coin)

# ==========================================
# ЛОГИКА СОЗДАНИЯ ЧЕКА
# ==========================================
async def create_check_logic(message: Message, amount: float, coin: str = 'USDT'):
    if amount <= 0:
        return await message.answer("Сумма должна быть больше 0")
    
    balance_field = f"{coin.lower()}_balance"
    
    con = get_db()
    cur = con.cursor()
    cur.execute(f"SELECT {balance_field} FROM users WHERE user_id = %s", (message.from_user.id,))
    row = cur.fetchone()
    
    if not row or row[0] < amount:
        cur.close()
        con.close()
        return await message.answer(f"Недостаточно {coin} на балансе.")
    
    cur.execute(f"UPDATE users SET {balance_field} = {balance_field} - %s WHERE user_id = %s", (amount, message.from_user.id))
    con.commit()
    
    cur.execute("INSERT INTO checks (creator_id, amount, coin, is_activated) VALUES (%s, %s, %s, false) RETURNING id", (message.from_user.id, amount, coin))
    check_id = cur.fetchone()[0]
    con.commit()
    cur.close()
    con.close()

    # Генерируем картинку
    img_path = generate_check_image(amount, coin)

    caption = f"Чек на {amount} {coin}\n\nЧтобы активировать, нажмите кнопку ниже."
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Получить {amount} {coin}", url=f"https://t.me/cryptobot?start=check_{check_id}")]
    ])
    
    photo = FSInputFile(img_path)
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        reply_markup=kb
    )

    if os.path.exists(img_path):
        os.remove(img_path)

# ==========================================
# АКТИВАЦИЯ ЧЕКА
# ==========================================
async def process_check_activation(message: Message, check_id: str):
    con = get_db()
    cur = con.cursor()
    
    cur.execute("SELECT amount, coin, is_activated FROM checks WHERE id = %s", (check_id,))
    row = cur.fetchone()
    
    if not row:
        await message.answer("Чек не найден.")
        cur.close(); con.close()
        return
    
    amount, coin, is_activated = row
    
    if is_activated:
        await message.answer("Этот чек уже активирован.")
        cur.close(); con.close()
        return
    
    balance_field = f"{coin.lower()}_balance"
    
    cur.execute(f"UPDATE users SET {balance_field} = {balance_field} + %s WHERE user_id = %s", (amount, message.from_user.id))
    cur.execute("UPDATE checks SET is_activated = true, activated_by = %s WHERE id = %s", (message.from_user.id, check_id))
    con.commit()
    cur.close()
    con.close()
    
    await message.answer(f"Вы активировали чек и получили {amount} {coin}!")

# ==========================================
# БАЛАНС
# ==========================================
@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT usdt_balance, gram_balance, sol_balance, trx_balance FROM users WHERE user_id = %s", (message.from_user.id,))
    row = cur.fetchone()
    cur.close()
    con.close()
    
    if not row:
        return await message.answer("У вас пока нет баланса. Купите крипту в мини-аппе!")
    
    await message.answer(
        f"Ваш баланс:\n"
        f"USDT: {row[0]}\n"
        f"GRAM: {row[1]}\n"
        f"SOL: {row[2]}\n"
        f"TRX: {row[3]}"
    )

# ==========================================
# СЧЕТ НА ОПЛАТУ (INVOICE)
# ==========================================
@dp.message(Command("invoice"))
async def cmd_create_invoice(message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Использование: /invoice 50 (где 50 — сумма в Stars)")
    
    try:
        stars = int(args[1])
    except:
        return await message.answer("Введите целое число. Например: /invoice 50")
    
    if stars <= 0:
        return await message.answer("Сумма должна быть больше 0")
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"Счет на {stars} Stars",
        description="Оплата счета. Вам будет начислено USDT.",
        payload=f"invoice_{stars}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=stars)]
    )

# ==========================================
# АДМИН-ПАНЕЛЬ
# ==========================================
@dp.message(Command("admin_panel"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обнулить все балансы", callback_data="reset_all_balances")]
    ])
    await message.answer("Админ-панель:", reply_markup=kb)

@dp.callback_query(F.data == "reset_all_balances")
async def reset_all_balances(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    con = get_db()
    cur = con.cursor()
    cur.execute("UPDATE users SET usdt_balance = 0, gram_balance = 0, sol_balance = 0, trx_balance = 0")
    con.commit()
    cur.close()
    con.close()
    await callback.message.answer("Все балансы обнулены.")
    await callback.answer()

# ==========================================
# ОПЛАТА (ОБРАБОТКА УСПЕШНЫХ ПЛАТЕЖЕЙ)
# ==========================================
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@dp.message(F.successful_payment)
async def success_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    
    # 1. Покупка крипты
    if payload.startswith("buycrypto_"):
        parts = payload.split("_")
        coin = parts[1]
        amount = float(parts[2])
        user_id = message.from_user.id
        
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
        
        if coin == "USDT": cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "GRAM": cur.execute("UPDATE users SET gram_balance = gram_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "SOL": cur.execute("UPDATE users SET sol_balance = sol_balance + %s WHERE user_id = %s", (amount, user_id))
        elif coin == "TRX": cur.execute("UPDATE users SET trx_balance = trx_balance + %s WHERE user_id = %s", (amount, user_id))
            
        con.commit()
        cur.close()
        con.close()
        await message.answer(f"Успешно куплено {amount} {coin}!")

    # 2. Оплата счета
    elif payload.startswith("invoice_"):
        stars = int(payload.replace("invoice_", ""))
        user_id = message.from_user.id
        
        usdt_to_add = stars * 0.01
        
        con = get_db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO users (user_id) VALUES (%s)", (user_id,))
            
        cur.execute("UPDATE users SET usdt_balance = usdt_balance + %s WHERE user_id = %s", (usdt_to_add, user_id))
        con.commit()
        cur.close()
        con.close()
        
        await message.answer(f"Счет на {stars} Stars оплачен!\nВам начислено {usdt_to_add} USDT.")

# ==========================================
# ВЕБ-СЕРВЕР (ДЛЯ МИНИ-АППА)
# ==========================================
async def handle_ping(request):
    return web.Response(text="OK")

async def handle_buy_request(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id"))
        coin = data.get("coin")
        amount = float(data.get("amount"))
        stars = int(data.get("stars"))

        await bot.send_invoice(
            chat_id=user_id,
            title=f"Покупка {amount} {coin}",
            description=f"Оплата {stars} Stars",
            payload=f"buycrypto_{coin}_{amount}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="XTR", amount=stars)],
        )
        return web.json_response({"status": "ok"})
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def start_web_server():
    app = web.Application()
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_credentials=True, expose_headers="*", allow_headers="*", allow_methods="*")
    })
    app.router.add_get('/', handle_ping)
    app.router.add_post('/buy', handle_buy_request)
    
    for route in list(app.router.routes()):
        cors.add(route)
        
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"ВЕБ-СЕРВЕР ЗАПУЩЕН НА ПОРТУ {port}")

# ==========================================
# ГЛАВНЫЙ ЗАПУСК
# ==========================================
async def main():
    logging.info("СТАРТ БОТА...")
    
    asyncio.create_task(start_web_server())
    
    try:
        logging.info("Проверка токена и API...")
        me = await bot.get_me()
        logging.info(f"Успешное подключение! Бот: @{me.username}")
    except Exception as e:
        logging.error(f"ОШИБКА ПОДКЛЮЧЕНИЯ К API MISSGRAM: {e}")
        return

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Вебхуки удалены, начинаем слушать сообщения...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"БОТ УПАЛ ВО ВРЕМЯ РАБОТЫ: {e}")

if __name__ == "__main__":
    asyncio.run(main())
