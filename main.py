import os
import logging
from dotenv import load_dotenv

# 📦 Імпорти з telegram.ext
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,  # ✅ Необхідно для обробки інлайн-кнопок
    filters
)

# 🧩 Імпорт функцій з модулів
from handlers.menu import show_main_menu
from handlers.monitoring import (
    start_monitoring_scene, token_a_input, token_b_input, enter_cross_rate,
    TOKEN_A, TOKEN_B, ENTER_RATE
)
from handlers.pairs import (
    start_pair_removal, handle_pair_selection, SELECTING
)

# 🛢️ Ініціалізація бази
from db import init_db

# 📝 Налаштування логування у файл bot.log
logging.basicConfig(
    filename="bot.log",
    filemode="a",
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 🔕 Відключення зайвих логів від httpx та Telegram
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._application").setLevel(logging.WARNING)

# 🔐 Завантаження .env і перевірка наявності токена
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("❌ BOT_TOKEN не знайдено в .env файлі!")
    exit(1)

# 📂 Ініціалізація бази даних
init_db()

# 🚀 Запуск Telegram Application
app = ApplicationBuilder().token(TOKEN).build()

# 📌 Команда /start → показ головного меню
app.add_handler(CommandHandler("start", show_main_menu))

# ➕ Сцена: додавання пари у моніторинг
monitor_scene = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Моніторити пару$"), start_monitoring_scene)],
    states={
        TOKEN_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_a_input)],
        TOKEN_B: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_b_input)],
        ENTER_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_cross_rate)],
    },
    fallbacks=[],
)
app.add_handler(monitor_scene)

# 📂 Сцена: перегляд та видалення моніторингових пар
remove_pairs_scene = ConversationHandler(
    # 1️⃣ Стартуємо сцену звичайним текстом «📂 Мої пари»
    entry_points=[
        MessageHandler(
            filters.Regex(r"^📂\s*Мої\s+пари$"),  # допускаємо пробіли/варіації
            start_pair_removal
        )
    ],
    # 2️⃣ Далі працюємо з інлайн-кнопками
    states={
        SELECTING: [CallbackQueryHandler(handle_pair_selection)],
    },
    fallbacks=[],
    per_chat=True        # ✅ досить per_chat; per_message нам не потрібний
    # (per_chat=True = ключ розмови - chat_id; CallbackQuery працює без обмежень)
)
app.add_handler(remove_pairs_scene)

# ▶️ Запуск бота 
logger.info("✅ Бот запущено")
app.run_polling()
