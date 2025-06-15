from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import logging

from services.pair_storage import (
    get_all_pairs,
    delete_pair_by_id,
    toggle_trade,
    set_potential,
    get_pair,            # невеличка утиліта: SELECT * FROM watched_pairs WHERE id = ?
)

logger = logging.getLogger(__name__)

# ─── СТАНИ ─────────────────────────────────────────────────────
SELECTING, ENTER_POTENTIAL = range(2)

# ─── КЛАВІАТУРА (одна пара = один рядок) ──────────────────────
def build_keyboard(pairs, selected: set[int] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    kb: list[list[InlineKeyboardButton]] = []

    for p in pairs:
        pair_id = p["id"]
        flag    = "✅" if pair_id in selected else "▫️"
        trade   = "🟢" if p["trade_open"] else "⚪️"
        pot     = f' 🎯{p["potential_move"]:+.1f}%' if p["potential_move"] is not None else ""
        label   = f"{flag} {trade} {p['token_a']}/{p['token_b']}{pot}"
        kb.append([
            InlineKeyboardButton(label, callback_data=f"pair_{pair_id}")
        ])

    kb.append([
        InlineKeyboardButton("🗑 Видалити обрані", callback_data="del"),
        InlineKeyboardButton("↩ Закрити",          callback_data="cancel")
    ])
    return InlineKeyboardMarkup(kb)


# ─── СТАРТ СЦЕНИ ───────────────────────────────────────────────
async def start_pair_removal(update: Update, context: CallbackContext):
    pairs = get_all_pairs()
    if not pairs:
        await update.message.reply_text("У вас немає пар для моніторингу.")
        return ConversationHandler.END

    context.user_data["sel"] = set()          # вибрані для видалення
    await update.message.reply_text(
        "🧾 Оберіть пари (натисніть по рядку),\n"
        "тисніть 🗑 для видалення або ⚪️/🟢 щоб позначити угоду,\n"
        "🎯 щоб вказати/змінити потенціал.",
        reply_markup=build_keyboard(pairs)
    )
    return SELECTING


# ─── CALLBACK-обробник ─────────────────────────────────────────
async def handle_pair_selection(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    data = q.data
    sel: set[int] = context.user_data.setdefault("sel", set())

    # ── 1. Вибір рядка (для видалення / дод.дій)
    if data.startswith("pair_"):
        pid = int(data.split("_")[1])
        # клацання по символах 2-й раз → показуємо меню дій
        if pid in sel:
            await show_actions_menu(q, pid)
            return SELECTING

        sel.add(pid)
        await q.edit_message_reply_markup(reply_markup=build_keyboard(get_all_pairs(), sel))
        return SELECTING

    # ── 2. Видалення
    if data == "del":
        if not sel:
            await q.edit_message_text("Жодна пара не вибрана.")
            return ConversationHandler.END
        for pid in sel: delete_pair_by_id(pid)
        await q.edit_message_text(f"✅ Видалено: {len(sel)}")
        return ConversationHandler.END

    # ── 3. Закриття
    if data == "cancel":
        await q.edit_message_text("↩")
        return ConversationHandler.END

    # ── 4. Дії зі специфічною парою ──────────────
    if data.startswith("act_"):
        _, action, pid_s = data.split("_")
        pid = int(pid_s)
        if action == "toggle":
            p = get_pair(pid)
            toggle_trade(pid, not p["trade_open"])
        elif action == "pot":
            context.user_data["pot_id"] = pid
            await q.message.reply_text("Введіть потенціал у %, 0 — скинути.")
            return ENTER_POTENTIAL

        # після дії повертаємось до основної таблиці
        await q.edit_message_reply_markup(reply_markup=build_keyboard(get_all_pairs(), sel))
        return SELECTING

    return SELECTING  # fallback


# ─── Введення потенціалу ───────────────────────────────────────
async def handle_potential_input(update: Update, context: CallbackContext):
    pid = context.user_data.pop("pot_id", None)
    if pid is None:
        return ConversationHandler.END

    text = update.message.text.replace(",", ".").strip()
    try:
        val = float(text)
        if val == 0:
            set_potential(pid, None)
        else:
            set_potential(pid, val)
    except ValueError:
        await update.message.reply_text("⚠️ Введіть число (можна з десятковою крапкою).")
        return ENTER_POTENTIAL

    await update.message.reply_text("🎯 Потенціал збережено.")
    return ConversationHandler.END


# ─── «Міні-меню» дій для однієї пари ───────────────────────────
async def show_actions_menu(query, pid: int):
    p = get_pair(pid)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔔 Угода: 🟢" if p["trade_open"] else "🔔 Угода: ⚪️",
                             callback_data=f"act_toggle_{pid}")
    ], [
        InlineKeyboardButton("🎯 Задати потенціал", callback_data=f"act_pot_{pid}")
    ], [
        InlineKeyboardButton("↩ Назад", callback_data="cancel")
    ]])
    await query.edit_message_reply_markup(reply_markup=kb)


# ─── ЗБІРКА ConversationHandler (підказка для main.py) ─────────
pairs_scene = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex(r"^📂\s*Мої\s+пари$"), start_pair_removal)],
    states={
        SELECTING: [
            CallbackQueryHandler(handle_pair_selection)
        ],
        ENTER_POTENTIAL: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_potential_input)
        ],
    },
    fallbacks=[],
)
