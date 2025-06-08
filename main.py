import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler
)
from handlers.menu import show_main_menu, menu_callback_router
from handlers.monitoring import start_monitoring  # уже реалізована сцена моніторингу
from db import init_db

# 1. Завантаження змінних з .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не знайдено в .env файлі!")

# 2. Ініціалізація бази даних
init_db()

# 3. Ініціалізація Telegram-додатку
app = ApplicationBuilder().token(TOKEN).build()

# 4. Команда /start — відкриває головне меню
app.add_handler(CommandHandler("start", show_main_menu))

# 5. Обробка кнопок головного меню
app.add_handler(CallbackQueryHandler(menu_callback_router))

# 6. Запуск бота
print("✅ Бот запущено. Очікуємо подій...")
app.run_polling()
