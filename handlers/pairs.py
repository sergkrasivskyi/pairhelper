from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler
from services.pair_storage import get_all_pairs, delete_pair_by_id
import logging

logger = logging.getLogger(__name__)

SELECTING = 0

# 🧩 Побудова інлайн-клавіатури з переліком пар
def build_pair_selection_keyboard(pairs, selected_ids=None):
    keyboard = []
    selected_ids = selected_ids or set()

    for pair in pairs:
        # Обробка даних як словник
        pair_id = pair["id"]
        token_a = pair["token_a"]
        token_b = pair["token_b"]
        is_selected = pair_id in selected_ids

        # Формуємо назву кнопки: 
        # ✅ якщо пара вибрана, або ▫️ якщо ні
        label = f"{'✅' if is_selected else '▫️'} {token_a}/{token_b}"
        callback_data = f"pairid_{pair_id}"
        keyboard.append([InlineKeyboardButton(label, callback_data=callback_data)])

    # Додаємо кнопку підтвердження видалення
    keyboard.append([
        InlineKeyboardButton("❌ Видалити обрані", callback_data="delete_selected")
    ])
    return InlineKeyboardMarkup(keyboard)

# ▶️ Старт сцени перегляду пар
async def start_pair_removal(update: Update, context: CallbackContext):
    logger.info("▶️ Викликано start_pair_removal")
    pairs = get_all_pairs()
    logger.info(f"🔍 Отримано {len(pairs)} пар: {pairs}")

    if not pairs:
        await update.message.reply_text("У вас немає пар для моніторингу.")
        return ConversationHandler.END

    context.user_data["selected_pairs"] = set()
    markup = build_pair_selection_keyboard(pairs)
    await update.message.reply_text("Оберіть пари для видалення:", reply_markup=markup)
    return SELECTING

# 🔄 Обробка натискань по інлайн-кнопках
async def handle_pair_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"🖱️ Обробка callback: {data}")

    if data.startswith("pairid_"):
        try:
            pair_id = int(data.split("_")[1])  # Отримуємо ID пари
            logger.info(f"✅ Обрано/знято пару з ID: {pair_id}")
        except (IndexError, ValueError) as e:
            logger.error(f"❌ Помилка обробки ID пари: {e}")
            await query.edit_message_text("⚠️ Некоректні дані пари.")
            return SELECTING

        # Перемикаємо вибір: додаємо або видаляємо з набору
        selected = context.user_data.setdefault("selected_pairs", set())
        if pair_id in selected:
            selected.remove(pair_id)
        else:
            selected.add(pair_id)

        # Перебудовуємо клавіатуру з оновленим вибором
        pairs = get_all_pairs()
        markup = build_pair_selection_keyboard(pairs, selected)
        await query.edit_message_reply_markup(reply_markup=markup)
        return SELECTING

    elif data == "delete_selected":
        selected = context.user_data.get("selected_pairs", set())
        logger.info(f"🗑️ Видаляємо пари: {selected}")

        if not selected:
            # Якщо жодна пара не вибрана, завершуємо розмову
            await query.edit_message_text("Жодну пару не обрано.")
            return ConversationHandler.END

        for pair_id in selected:
            delete_pair_by_id(pair_id)

        await query.edit_message_text(f"✅ Видалено пар: {len(selected)}")
        context.user_data["selected_pairs"] = set()
        return ConversationHandler.END

    logger.warning(f"⚠️ Незрозуміле callback data: {data}")
    return SELECTING
