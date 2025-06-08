import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters
)
from handlers.menu import show_main_menu
from handlers.monitoring import (
    start_monitoring_scene, token_a_input, token_b_input, enter_cross_rate,
    TOKEN_A, TOKEN_B, ENTER_RATE
)
from db import init_db

# ✅ Логування напряму у bot.log
logging.basicConfig(
    filename="bot.log",
    filemode="a",
    encoding="utf-8", 
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext._application").setLevel(logging.WARNING)

# ✅ Завантаження змінних
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    logger.error("❌ BOT_TOKEN не знайдено в .env файлі!")
    exit(1)

init_db()

app = ApplicationBuilder().token(TOKEN).build()

# /start → головне меню
app.add_handler(CommandHandler("start", show_main_menu))

# ➕ Моніторити пару
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

logger.info("✅ Бот запущено")
app.run_polling()
