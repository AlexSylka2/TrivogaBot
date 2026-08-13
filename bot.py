import asyncio
import datetime
import requests
import json
import logging
import os
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import folium
from aiohttp import web

logging.basicConfig(level=logging.INFO)

API_TOKEN = "8689374722:AAEPz3VxmJ1hZ-I_TYho7gvCDTJCJJuJZzg"  # твій токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

REGIONS_FILE = "regions.json"
SETTINGS_FILE = "settings.json"

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_region = load_json(REGIONS_FILE)
user_settings = load_json(SETTINGS_FILE)

# ---------- МЕНЮ ----------
def main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Регион", callback_data="region")],
        [InlineKeyboardButton(text="🗺️ Карта", callback_data="map")],
        [InlineKeyboardButton(text="🚨 Статус", callback_data="status")],
        [InlineKeyboardButton(text="📜 История", callback_data="history")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🌐 Все тревоги", callback_data="alerts")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="➡️ Вперед", callback_data="next")]
    ])
    return keyboard

def second_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❌ Выход", callback_data="exit")]
    ])
    return keyboard

def settings_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
    ])
    return keyboard

# ---------- КОМАНДЫ ----------
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я бот тревог.\nВыберите действие:", reply_markup=main_menu())

@router.message(Command("help"))
async def help(message: types.Message):
    await message.answer(
        "/start — меню\n"
        "/map — карта тревог по областям\n"
        "/status — статус тревоги\n"
        "/history — последние тревоги\n"
        "/stats — статистика тревог\n"
        "/alerts — все активные тревоги\n"
        "/region <название> — выбрать регион"
    )

# ---------- ОБРАБОТКА КНОПОК ----------
@router.callback_query(lambda c: c.data == "region")
async def cb_region(callback: types.CallbackQuery):
    await callback.message.answer("📍 Выберите регион командой /region <название>")
    await callback.answer()

@router.callback_query(lambda c: c.data == "map")
async def cb_map(callback: types.CallbackQuery):
    await map_command(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "status")
async def cb_status(callback: types.CallbackQuery):
    await status(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "history")
async def cb_history(callback: types.CallbackQuery):
    await history(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    await stats(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "alerts")
async def cb_alerts(callback: types.CallbackQuery):
    await alerts(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "help")
async def cb_help(callback: types.CallbackQuery):
    await help(callback.message)
    await callback.answer()

@router.callback_query(lambda c: c.data == "next")
async def cb_next(callback: types.CallbackQuery):
    await callback.message.answer("➡️ Второе меню:", reply_markup=second_menu())
    await callback.answer()

@router.callback_query(lambda c: c.data == "back")
async def cb_back(callback: types.CallbackQuery):
    await callback.message.answer("⬅️ Главное меню:", reply_markup=main_menu())
    await callback.answer()

@router.callback_query(lambda c: c.data == "settings")
async def cb_settings(callback: types.CallbackQuery):
    await callback.message.answer("⚙️ Настройки:", reply_markup=settings_menu())
    await callback.answer()

@router.callback_query(lambda c: c.data == "exit")
async def cb_exit(callback: types.CallbackQuery):
    await callback.message.answer("❌ Выход из меню")
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("lang_"))
async def cb_lang(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await callback.message.answer(f"✅ Язык установлен: {lang}")
    await callback.answer()

# ---------- МОНИТОРИНГ ----------
async def monitor_alerts():
    last_alerts = {}
    while True:
        try:
            url = "https://mapa.ua/api/v1/current"
            data = requests.get(url).json()
            if "alerts" in data and data["alerts"]:
                current_alerts = {alert.get("region") for alert in data["alerts"]}
                for user_id, region in user_region.items():
                    if region in current_alerts:
                        if region not in last_alerts.get(user_id, set()):
                            await bot.send_message(chat_id=int(user_id), text=f"🚨 Нова тривога у {region}!")
                    last_alerts[user_id] = current_alerts
            else:
                last_alerts = {}
        except Exception as e:
            print(f"Помилка моніторингу: {e}")
        await asyncio.sleep(30)

# ---------- ЗАПУСК ----------
async def main():
    print("Бот запущен и слушает команды...")
    asyncio.create_task(monitor_alerts())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# ---------- WEB ENDPOINT ДЛЯ RENDER ----------
async def handle(request):
    return web.Response(text="Bot is running")

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

