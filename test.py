import threading
import queue
import time
from flask import Flask, request
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

TOKEN = "8414425043:AAGpuiIcPRqkdk8E8BnralR7D3aR3i--5wo"
CHAT_ID = 995726423
LINK_URL = "https://agriyeildprediction.netlify.app/"

latest_data = {"soil": 0, "temp": 0.0, "humidity": 0.0}

LINK_TEXTS = {
    "en": "View Crop Yield Prediction Tool🔗",
    "hi": "फसल उपज भविष्यवाणी उपकरण देखें🔗",
    "kn": "ಬೆಳೆ ಇಳುವರಿ ಮುನ್ಸೂಚನೆ ಸಾಧನ ವೀಕ್ಷಿಸಿ🔗"
}

user_language = None 
NOTIFY_INTERVAL = 3600

tasks_queue = queue.Queue()
application: Application = None 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! You will receive sensor data here.\n"
        "The language selection menu will appear hourly."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_language
    msg = update.message.text.strip()

    if msg == "1":
        user_language = "en"
    elif msg == "2":
        user_language = "hi"
    elif msg == "3":
        user_language = "kn"
    else:
        await update.message.reply_text("Please reply with 1, 2, or 3 to select language, or use /sendmenu.")
        return

    soil = latest_data["soil"]
    temp = latest_data["temp"]
    humidity = latest_data["humidity"]
    
    if user_language == "en":
        response = (
            f"✅ Language set to English.\n\n"
            f"Current Data:\nSoil: {soil}%\nTemp: {temp}°C\nHumidity: {humidity}%\n"
            f"<a href='{LINK_URL}'>{LINK_TEXTS['en']}</a>"
        )
    elif user_language == "hi":
        response = (
            f"✅ भाषा हिंदी पर सेट है।\n\n"
            f"वर्तमान डेटा:\nमिट्टी: {soil}%\nतापमान: {temp}°C\nआर्द्रता: {humidity}%\n"
            f"<a href='{LINK_URL}'>{LINK_TEXTS['hi']}</a>"
        )
    elif user_language == "kn":
        response = (
            f"✅ ಭಾಷೆಯನ್ನು ಕನ್ನಡಕ್ಕೆ ಹೊಂದಿಸಲಾಗಿದೆ.\n\n"
            f"ಪ್ರಸ್ತುತ ಡೇಟಾ:\nಮಣ್ಣು: {soil}%\nತಾಪಮಾನ: {temp}°C\nಆರ್ದ್ರತೆ: {humidity}%\n"
            f"<a href='{LINK_URL}'>{LINK_TEXTS['kn']}</a>"
        )

    await update.message.reply_text(response, parse_mode=constants.ParseMode.HTML)


async def send_menu_to_user(update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    global user_language
    
    target_chat_id = CHAT_ID
    if update and update.effective_chat:
        target_chat_id = update.effective_chat.id

    menu_text = (
        "🌾 New sensor data received!\n\n"
        "भाषा चुनें / Select Language / ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ:\n"
        "1️⃣ English\n2️⃣ हिंदी\n3️⃣ ಕನ್ನಡ"
    )
    try:
        await application.bot.send_message(chat_id=target_chat_id, text=menu_text)
        print("✅ Language selection menu sent.")
        
        user_language = None 

    except Exception as e:
        print(f"❌ Error sending menu to {target_chat_id}:", e)


async def periodic_menu_sender(app: Application):
    await asyncio.sleep(5) 
    print(f"⏰ Starting hourly menu sender. Interval: {NOTIFY_INTERVAL} seconds.")
    
    while True:
        try:
            await send_menu_to_user(update=None, context=None)
        except Exception as e:
            print(f"❌ Error in periodic_menu_sender: {e}")
            
        await asyncio.sleep(NOTIFY_INTERVAL)


flask_app = Flask(__name__)

@flask_app.route("/sensor", methods=["POST"])
def receive_sensor():
    global latest_data
    try:
        data = request.get_json(force=True)
    except:
        return "Invalid JSON", 400
        
    latest_data["soil"] = data.get("soil", latest_data["soil"])
    latest_data["temp"] = data.get("temp", latest_data["temp"])
    latest_data["humidity"] = data.get("humidity", latest_data["humidity"])

    print("Received from ESP32:", latest_data)

    return "Sensor data received!", 200

def run_flask():
    print("📢 Starting Flask server...")
    flask_app.run(host="0.0.0.0", port=5000, use_reloader=False)

async def process_tasks(app: Application):
    while True:
        try:
            task_coroutine = tasks_queue.get_nowait()
        except queue.Empty:
            await asyncio.sleep(1)
            continue
            
        print("💡 Task found in queue, running...")
        try:
            await task_coroutine
        except Exception as e:
            print(f"❌ Error running task: {e}")

async def on_startup(app: Application):
    app.create_task(process_tasks(app))
    print("✅ Asynchronous task processor started.")
    
    app.create_task(periodic_menu_sender(app))
    print("✅ Hourly menu sender task created.")

def main():
    global application
    
    application = Application.builder().token(TOKEN).post_init(on_startup).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sendmenu", send_menu_to_user)) 
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    print("✅ Bot is running and waiting for updates...")
    application.run_polling()

if __name__ == "__main__":
    main()