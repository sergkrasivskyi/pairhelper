from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("➕ Моніторити пару", callback_data="monitor_pair"),
            InlineKeyboardButton("📊 Відкрити угоду", callback_data="open_trade")
        ],
        [
            InlineKeyboardButton("📂 Мої пари", callback_data="my_pairs"),
            InlineKeyboardButton("📉 Активні угоди", callback_data="active_trades")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Оберіть дію:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Оберіть дію:", reply_markup=reply_markup)
