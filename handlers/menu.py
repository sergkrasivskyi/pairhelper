from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("➕ Моніторити пару"), KeyboardButton("📊 Відкрити угоду")],
        [KeyboardButton("📂 Мої пари"), KeyboardButton("📉 Активні угоди")]
    ],
    resize_keyboard=True
)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Оберіть дію:", reply_markup=menu_keyboard) 
