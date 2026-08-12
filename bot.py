import asyncio
import datetime
import requests
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import folium

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

@router.message(Command("region"))
async def set_region(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        region = args[1]
        user_region[str(message.from_user.id)] = region
        save_json(REGIONS_FILE, user_region)
        await message.answer(f"✅ Регион установлен: {region}")
        await status(message)
    else:
        await message.answer("⚠️ Укажите регион, например: /region Киев")

@router.message(Command("status"))
async def status(message: types.Message):
    try:
        url = "https://mapa.ua/api/v1/current"
        data = requests.get(url).json()
        if "alerts" in data and data["alerts"]:
            region = user_region.get(str(message.from_user.id))
            if region:
                alerts = [a for a in data["alerts"] if a.get("region") == region]
                if alerts:
                    response_text = f"🚨 Тривога у {region}:\n"
                    for alert in alerts:
                        started = alert.get("started_at")
                        if started:
                            start_time = datetime.datetime.fromtimestamp(started).strftime("%H:%M")
                            response_text += f"• Початок {start_time}\n"
                    await message.answer(response_text)
                else:
                    await message.answer(f"✅ У {region} зараз тривог немає")
            else:
                response_text = "🚨 Активні тривоги:\n"
                for alert in data["alerts"]:
                    response_text += f"• {alert.get('region')}\n"
                await message.answer(response_text)
        else:
            await message.answer("✅ Зараз тривог немає")
    except Exception as e:
        await message.answer("⚠️ Помилка при отриманні даних")
        print(f"Помилка: {e}")

@router.message(Command("map"))
async def map_command(message: types.Message):
    m = folium.Map(location=[48.3794, 31.1656], zoom_start=6)
    url = "https://mapa.ua/api/v1/current"
    data = requests.get(url).json()
    active_alerts = {alert.get("region") for alert in data.get("alerts", [])}
    geojson_url = "https://raw.githubusercontent.com/deldersveld/topojson/master/countries/ukraine/ukraine-regions.json"
    folium.GeoJson(
        geojson_url,
        style_function=lambda feature: {
            "fillColor": "red" if feature["properties"]["name"] in active_alerts else "green",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.5,
        },
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Область"])
    ).add_to(m)
    m.save("map.html")
    await message.answer_document(FSInputFile("map.html"))

@router.message(Command("history"))
async def history(message: types.Message):
    try:
        url = "https://mapa.ua/api/v1/history"
        data = requests.get(url).json()
        region = user_region.get(str(message.from_user.id))
        response_text = "📜 Останні тривоги:\n"
        count = 0
        for alert in data.get("alerts", []):
            if not region or alert.get("region") == region:
                started = alert.get("started_at")
                ended = alert.get("ended_at")
                start_time = datetime.datetime.fromtimestamp(started).strftime("%d.%m %H:%M") if started else "?"
                end_time = datetime.datetime.fromtimestamp(ended).strftime("%H:%M") if ended else "?"
                response_text += f"• {alert.get('region')} — {start_time} до {end_time}\n"
                count += 1
                if count >= 5:
                    break
        await message.answer(response_text)
    except Exception as e:
        await message.answer("⚠️ Помилка при отриманні історії")
        print(f"Помилка: {e}")

@router.message(Command("stats"))
async def stats(message: types.Message):
    try:
        url = "https://mapa.ua/api/v1/history"
        data = requests.get(url).json()
        region = user_region.get(str(message.from_user.id))
        if not region:
            await message.answer("⚠️ Сначала выберите регион командой /region <название>")
            return
        alerts = [a for a in data.get("alerts", []) if a.get("region") == region]
        total = len(alerts)
        durations = []
        for alert in alerts:
            if alert.get("started_at") and alert.get("ended_at"):
                durations.append(alert.get("ended_at") - alert.get("started_at"))
        avg_duration = sum(durations)/len(durations) if durations else 0
        avg_minutes = int(avg_duration/60)
        await message.answer(
            f"📊 Статистика по {region}:\n"
            f"• Всего тревог: {total}\n"
            f"• Средняя длительность: {avg_minutes} мин"
        )
    except Exception as e:
        await message.answer("⚠️ Ошибка при получении статистики")
        print(f"Ошибка: {e}")

@router.message(Command("alerts"))
async def alerts(message: types.Message):
    try:
        url = "https://mapa.ua/api/v1/current"
        data = requests.get(url).json()
        if "alerts" in data and data["alerts"]:
            response_text = "🚨 Активні тривоги по Україні:\n"
            for alert in data["alerts"]:
                response_text += f"• {alert.get('region')}\n"
            await message.answer(response_text)
        else:
            await message.answer("✅ Зараз тривог немає по Україні")
    except Exception as e:
        await message.answer("⚠️ Помилка при отриманні даних")
        print(f"Помилка: {e}")

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
import os
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running")

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
