from telegram.ext import ApplicationBuilder, CommandHandler, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.monitoring import start_monitoring, token_a_input, token_b_input, choose_mode, manual_rate_input
from db import init_db

init_db()

app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

monitor_conv = ConversationHandler(
    entry_points=[CommandHandler("monitor_pair", start_monitoring)],
    states={
        0: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_a_input)],
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, token_b_input)],
        2: [CallbackQueryHandler(choose_mode)],
        3: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_rate_input)],
    },
    fallbacks=[],
)

app.add_handler(monitor_conv)

print("Бот запущено")
app.run_polling()
