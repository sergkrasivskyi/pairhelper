import os
import logging
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

# ── Хендлери меню
from handlers.menu import show_main_menu

# ── Сцена «Моніторити пару»
from handlers.monitoring import (
    start_monitoring_scene, handle_pair_input,
    handle_crossrate_choice, handle_manual_crossrate,
    AWAITING_PAIR_INPUT, AWAITING_CROSSRATE_DECISION, AWAITING_MANUAL_CROSSRATE
)

# ── Сцена «Мої пари»
from handlers.pairs import start_pair_removal, handle_pair_selection, SELECTING

from db import init_db

# ──────────────────────────────────────────────────────────────
# Логування
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="bot.log",
    filemode="a",
    encoding="utf-8",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ──────────────────────────────────────────────────────────────
# Токен
# ──────────────────────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.error("❌ BOT_TOKEN не знайдено!")
    exit(1)

# ──────────────────────────────────────────────────────────────
# 1. База даних
# ──────────────────────────────────────────────────────────────
init_db()

# ──────────────────────────────────────────────────────────────
# 2. Створення бота
# ──────────────────────────────────────────────────────────────
app = ApplicationBuilder().token(TOKEN).build()

# /start → головне меню
app.add_handler(CommandHandler("start", show_main_menu))

# ➕ Сцена «Моніторити пару»
monitor_scene = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"^➕\s*Моніторити\s+пару$"), start_monitoring_scene)
    ],
    states={
        AWAITING_PAIR_INPUT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pair_input)
        ],
        AWAITING_CROSSRATE_DECISION: [
            CallbackQueryHandler(handle_crossrate_choice)
        ],
        AWAITING_MANUAL_CROSSRATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_crossrate)
        ],
    },
    fallbacks=[],
    per_chat=True
)
app.add_handler(monitor_scene)

# 📂 Сцена «Мої пари»
pairs_scene = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(r"^📂\s*Мої\s+пари$"), start_pair_removal)
    ],
    states={
        SELECTING: [CallbackQueryHandler(handle_pair_selection)],
    },
    fallbacks=[],
    per_chat=True
)
app.add_handler(pairs_scene)

# ──────────────────────────────────────────────────────────────
logger.info("✅ Бот запущено")
app.run_polling()
