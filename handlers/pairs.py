from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler
from services.pair_storage import get_all_pairs, delete_pair_by_id

SELECTING = 0

# 🧩 Побудова інлайн-клавіатури з переліком пар
def build_pair_selection_keyboard(pairs):
    keyboard = []
    for pair in pairs:
        # ✅ Обробляємо як словник, а не як кортеж
        pair_id = pair["id"]
        token_a = pair["token_a"]
        token_b = pair["token_b"]
        callback_data = f"pairid_{pair_id}"  # Унікальний ID кожної кнопки
        text = f"{token_a}/{token_b}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    # ⬇️ Додаємо кнопку підтвердження видалення
    keyboard.append([InlineKeyboardButton("❌ Видалити обрані", callback_data="delete_selected")])
    return InlineKeyboardMarkup(keyboard)

# ▶️ Старт сцени перегляду пар
async def start_pair_removal(update: Update, context: CallbackContext):
    pairs = get_all_pairs()
    if not pairs:
        await update.message.reply_text("У вас немає пар для моніторингу.")
        return ConversationHandler.END

    markup = build_pair_selection_keyboard(pairs)
    await update.message.reply_text("Оберіть пари для видалення:", reply_markup=markup)

    # ⏳ Створюємо тимчасовий список для обраних пар
    context.user_data["selected_pairs"] = set()
    return SELECTING

# 🔄 Обробка натискань по інлайн-кнопках
async def handle_pair_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("pairid_"):
        try:
            pair_id = int(data.split("_")[1])  # ✅ Коректне виділення ID
        except (IndexError, ValueError):
            await query.edit_message_text("⚠️ Некоректні дані пари.")
            return SELECTING

        # 🧠 Перемикаємо пару: обрано ↔ не обрано
        selected = context.user_data.setdefault("selected_pairs", set())
        if pair_id in selected:
            selected.remove(pair_id)
        else:
            selected.add(pair_id)

        await query.edit_message_text(
            f"Обрано пар: {len(selected)}\nНатисніть ❌ Видалити обрані, щоб підтвердити."
        )

    elif data == "delete_selected":
        selected = context.user_data.get("selected_pairs", set())
        if not selected:
            await query.edit_message_text("Жодну пару не обрано.")
            return SELECTING

        for pair_id in selected:
            delete_pair_by_id(pair_id)

        await query.edit_message_text(f"✅ Видалено пар: {len(selected)}")
        context.user_data["selected_pairs"] = set()
        return ConversationHandler.END

    return SELECTING
