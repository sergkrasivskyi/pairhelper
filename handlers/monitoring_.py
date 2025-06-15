from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.cross_rate import get_cross_rate
from services.pair_storage import add_watched_pair

# ──────────────────────────────────────────────────────────────
# СТАНИ ConversationHandler
# ──────────────────────────────────────────────────────────────
AWAITING_PAIR_INPUT, AWAITING_CROSSRATE_DECISION, AWAITING_MANUAL_CROSSRATE = range(3)

# Тимчасові дані по користувачах
temp_data: dict[int, dict] = {}

# ──────────────────────────────────────────────────────────────
# ▶️ Старт сцени «Моніторити пару»
# ──────────────────────────────────────────────────────────────
async def start_monitoring_scene(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Очищуємо можливу попередню сцену
    context.user_data.clear()

    msg = await update.message.reply_text(
        "Введіть пару **або кілька пар** через пробіл у форматі:\n"
        "`BTC/ETH` або `C98/PHA NTRN/RDNT ...`",
        parse_mode="Markdown"
    )
    context.user_data["scene_messages"] = [msg.message_id]
    return AWAITING_PAIR_INPUT

# ──────────────────────────────────────────────────────────────
# 📥 Обробка введених пар
# ──────────────────────────────────────────────────────────────
async def handle_pair_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    text = update.message.text.strip().upper()
    context.user_data["scene_messages"].append(update.message.message_id)

    pairs = text.split()
    if not pairs:
        await update.message.reply_text("⚠️ Не знайдено пар у повідомленні.")
        return AWAITING_PAIR_INPUT

    # ▸ 1. Багато пар — додаємо автоматично
    if len(pairs) > 1:
        added, failed = [], []
        for pr in pairs:
            try:
                tok_a, tok_b = pr.split("/")
                rate = await get_cross_rate(tok_a, tok_b)
                add_watched_pair(tok_a, tok_b, rate)
                added.append(f"{tok_a}/{tok_b} ({rate:.6f})")
            except Exception as e:
                failed.append(f"{pr} ❌ ({e})")

        msg = ""
        if added:
            msg += "✅ Додано:\n" + "\n".join(added)
        if failed:
            msg += "\n\n❌ Не вдалося:\n" + "\n".join(failed)

        await update.message.reply_text(msg or "Нічого не додано.")
        return ConversationHandler.END

    # ▸ 2. Одна пара — пропонуємо Auto / Manual
    try:
        tok_a, tok_b = pairs[0].split("/")
    except ValueError:
        await update.message.reply_text("⚠️ Формат має бути `TOKEN1/TOKEN2`.")
        return AWAITING_PAIR_INPUT

    temp_data[user_id] = {"pair": (tok_a, tok_b)}

    buttons = [
        [InlineKeyboardButton("🔄 Авто-кроскурс", callback_data="auto")],
        [InlineKeyboardButton("✍️ Ввести вручну", callback_data="manual")]
    ]
    await update.message.reply_text(
        f"Пара **{tok_a}/{tok_b}**.\nОбери спосіб визначення кроскурсу:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )
    return AWAITING_CROSSRATE_DECISION

# ──────────────────────────────────────────────────────────────
# ⚙️ Обробка вибору Auto / Manual
# ──────────────────────────────────────────────────────────────
async def handle_crossrate_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    tok_a, tok_b = temp_data[user_id]["pair"]

    if query.data == "auto":
        try:
            rate = await get_cross_rate(tok_a, tok_b)
            add_watched_pair(tok_a, tok_b, rate)
            await query.edit_message_text(f"✅ Додано {tok_a}/{tok_b} з курсом {rate:.6f}")
        except Exception as e:
            await query.edit_message_text(f"❌ Помилка: {e}")
        return ConversationHandler.END

    if query.data == "manual":
        await query.edit_message_text(f"✍️ Введіть курс для {tok_a}/{tok_b}:")
        return AWAITING_MANUAL_CROSSRATE

    await query.edit_message_text("⚠️ Невідома команда.")
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────
# ✍️ Ручне введення кроскурсу
# ──────────────────────────────────────────────────────────────
async def handle_manual_crossrate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    tok_a, tok_b = temp_data[user_id]["pair"]

    try:
        rate = float(update.message.text.replace(",", "."))
        add_watched_pair(tok_a, tok_b, rate)
        await update.message.reply_text(f"✅ Додано {tok_a}/{tok_b} з курсом {rate}")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("⚠️ Введіть числове значення курсу.")
        return AWAITING_MANUAL_CROSSRATE
