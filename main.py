# main.py
# ───────────────────────────────────────────────────────────────
# 1. SYSTEM & ENV
# ───────────────────────────────────────────────────────────────
import os, logging, warnings, asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise SystemExit("❌ BOT_TOKEN не знайдено в .env!")

# ───────────────────────────────────────────────────────────────
# 2. LOGGING / MUTE PTB WARNINGS
# ───────────────────────────────────────────────────────────────
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

# ───────────────────────────────────────────────────────────────
# 3. DB INIT
# ───────────────────────────────────────────────────────────────
from db import init_db
init_db()

# ───────────────────────────────────────────────────────────────
# 4. ЄДИНИЙ event-loop  →  for PTB + APScheduler
# ───────────────────────────────────────────────────────────────
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# ───────────────────────────────────────────────────────────────
# 5. TELEGRAM Application
# ───────────────────────────────────────────────────────────────
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters
)

app = (
    ApplicationBuilder()
    .token(TOKEN)
    .concurrent_updates(True)      # ← залиште/приберіть за потреби
    .build()
)

# ───────────────────────────────────────────────────────────────
# 6. HANDLERS
# ───────────────────────────────────────────────────────────────
## 6.1  /start → меню
from handlers.menu import show_main_menu
app.add_handler(CommandHandler("start", show_main_menu))

## 6.2  «Моніторити пару»
from handlers.monitoring import (
    start_monitoring_scene, handle_pair_input,
    handle_crossrate_choice, handle_manual_crossrate,
    AWAITING_PAIR_INPUT, AWAITING_CROSSRATE_DECISION,
    AWAITING_MANUAL_CROSSRATE,
)
monitor_scene = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"^➕\s*Моніторити\s+пару$"),
                                 start_monitoring_scene)],
    states = {
        AWAITING_PAIR_INPUT         : [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                                      handle_pair_input)],
        AWAITING_CROSSRATE_DECISION : [CallbackQueryHandler(handle_crossrate_choice)],
        AWAITING_MANUAL_CROSSRATE   : [MessageHandler(filters.TEXT & ~filters.COMMAND,
                                                      handle_manual_crossrate)],
    },
    fallbacks=[]
)
app.add_handler(monitor_scene)

## 6.3  «Мої пари» (оновлений файл pairs.py уже містить свій ConversationHandler)
from handlers.pairs import pairs_scene
app.add_handler(pairs_scene)

# ───────────────────────────────────────────────────────────────
# 7. APScheduler-jobs (pulse 15 хв, hourly report)
# ───────────────────────────────────────────────────────────────
# ─── APScheduler ──────────────────────────────────────────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron      import CronTrigger         
from services.pulse15               import pulse
from services.hourly_report         import hourly_report

sched = AsyncIOScheduler(event_loop=loop, timezone="UTC")

# 15-хв «пульс» саме у 00, 15, 30, 45 хв.
pulse_trigger = CronTrigger(minute="0,15,30,45", timezone="UTC")
sched.add_job(
    pulse,
    pulse_trigger,
    id="pulse15",
    args=[app.bot],
    coalesce=True,            # якщо минулий запуск ще виконується – не плодити новий
    misfire_grace_time=90     # якщо проспали ≤90 с – виконаємо відразу
)

# Щогодинний підсумок рівно о 00 хв кожної години
hourly_trigger = CronTrigger(minute="0", timezone="UTC")
sched.add_job(
    hourly_report,
    hourly_trigger,
    id="hourly",
    args=[app.bot],
    misfire_grace_time=300
)

sched.start()

# ───────────────────────────────────────────────────────────────
logger.info("✅ Бот запущено")
app.run_polling(close_loop=False)          # ←  НІЯКОГО параметра loop!
