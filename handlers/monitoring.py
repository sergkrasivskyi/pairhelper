from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CallbackContext, MessageHandler, CallbackQueryHandler, filters
from services.binance_api import get_price_usdt
from db import add_watched_pair

TOKEN_A, TOKEN_B, CHOOSE_MODE, ENTER_RATE = range(4)
temp_data = {}

def start_monitoring(update: Update, context: CallbackContext):
    update.message.reply_text("Введи перший токен (наприклад, BNB):")
    return TOKEN_A

def token_a_input(update: Update, context: CallbackContext):
    temp_data[update.effective_user.id] = {'token_a': update.message.text.upper()}
    update.message.reply_text("Введи другий токен (наприклад, ETH):")
    return TOKEN_B

def token_b_input(update: Update, context: CallbackContext):
    temp_data[update.effective_user.id]['token_b'] = update.message.text.upper()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Авто-розрахунок", callback_data="auto")],
        [InlineKeyboardButton("✍️ Ввести вручну", callback_data="manual")]
    ])
    update.message.reply_text("Як отримати крос-курс?", reply_markup=keyboard)
    return CHOOSE_MODE

def choose_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    token_a = temp_data[user_id]['token_a']
    token_b = temp_data[user_id]['token_b']

    if query.data == "auto":
        price_a = get_price_usdt(token_a)
        price_b = get_price_usdt(token_b)
        cross_rate = price_a / price_b
        add_watched_pair(token_a, token_b, cross_rate)
        query.edit_message_text(f"Пара {token_a}/{token_b} додана з курсом {cross_rate:.6f}")
        return ConversationHandler.END
    else:
        query.edit_message_text("Введи стартовий крос-курс вручну:")
        return ENTER_RATE

def manual_rate_input(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    try:
        rate = float(update.message.text)
        token_a = temp_data[user_id]['token_a']
        token_b = temp_data[user_id]['token_b']
        add_watched_pair(token_a, token_b, rate)
        update.message.reply_text(f"Пара {token_a}/{token_b} додана з курсом {rate}")
    except ValueError:
        update.message.reply_text("Некоректний формат. Введи число.")
        return ENTER_RATE
    return ConversationHandler.END
