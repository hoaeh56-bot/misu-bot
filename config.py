# config.py
import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env (для локального запуска)
load_dotenv()

# Берем значения из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_SERVER = os.getenv("API_SERVER", "https://misugram.cloud-ip.cc")
DATABASE_URL = os.getenv("DATABASE_URL")

# Проверка, чтобы бот не упал молча
if not BOT_TOKEN or not DATABASE_URL:
    raise ValueError("КРИТИЧЕСКАЯ ОШИБКА: Не заданы BOT_TOKEN или DATABASE_URL в окружении!")
