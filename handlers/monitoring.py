"""
Сцена «➕ Моніторити пару»

• Підтримує введення **однієї** або **декількох** пар
  у форматі `ABC/XYZ` через пробіл.
• Для однієї пари запитує спосіб отримання крос-курсу
  (авто ↔ ручне введення).
• Дані записуються у watched_pairs (services.pair_storage.add_watched_pair).

‼  Важливо:  add_watched_pair() приймає 4-й аргумент *user_id*,
             тому ВСІ виклики передають ID поточного користувача.
"""
from __future__ import annotations

import asyncio, re
from typing import List

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes, ConversationHandler
)

from services.cross_rate   import get_cross_rate
from services.pair_storage import add_watched_pair


# ───────────────────────── СТАНИ ─────────────────────────
AWAITING_PAIR_INPUT, AWAITING_CROSSRATE_DECISION, AWAITING_MANUAL_CROSSRATE = range(3)
PAIR_RE = re.compile(r"^[A-Z0-9]+/[A-Z0-9]+$")


# ╭──────────────────────────────────────────────────────────╮
# │ ▶️ Старт сцени                                          │
# ╰──────────────────────────────────────────────────────────╯
async def start_monitoring_scene(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    # «грубо» очищаємо user_data, щоби не чіплятись за попередню сцену
    context.user_data.clear()

    msg = await update.message.reply_text(
        "Введіть **одну** або **декілька** пар через пробіл:\n"
        "`BTC/ETH`   `C98/PHA NTRN/RDNT` …",
        parse_mode="Markdown"
    )
    context.user_data["scene_messages"] = [msg.message_id]
    return AWAITING_PAIR_INPUT


# ╭──────────────────────────────────────────────────────────╮
# │ 📥 Введення пар                                         │
# ╰──────────────────────────────────────────────────────────╯
async def handle_pair_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    text  = update.message.text.strip().upper()
    uid   = update.effective_user.id
    context.user_data["scene_messages"].append(update.message.message_id)

    pairs: List[str] = text.split()
    if not pairs:
        await update.message.reply_text("⚠️ Не знайдено жодної пари.")
        return AWAITING_PAIR_INPUT

    # валідація формату
    invalid = [p for p in pairs if not PAIR_RE.fullmatch(p)]
    if invalid:
        await update.message.reply_text(
            "⚠️ Неприпустимий формат:\n" + "\n".join(invalid)
        )
        return AWAITING_PAIR_INPUT

    # ▸ Декілька пар — одразу Auto
    if len(pairs) > 1:
        await _add_many_pairs(pairs, uid, update)
        return await _finish(update, context)

    # ▸ Одна пара — Auto / Manual
    tok_a, tok_b = pairs[0].split("/")
    context.user_data["pair"] = (tok_a, tok_b, uid)

    kb = [
        [InlineKeyboardButton("🔄 Авто-кроскурс", callback_data="auto")],
        [InlineKeyboardButton("✍️ Ввести вручну", callback_data="manual")]
    ]
    await update.message.reply_text(
        f"Пара **{tok_a}/{tok_b}**.\nОберіть спосіб визначення кроскурсу:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )
    return AWAITING_CROSSRATE_DECISION


# ─────────────────────────────────────────────────────────────
async def _add_many_pairs(
    pairs: List[str],
    user_id: int,
    update: Update
) -> None:
    """Паралельно додає декілька пар (auto cross-rate)."""
    added, failed = [], []

    tokens, coros = [], []
    for p in pairs:
        ta, tb = p.split("/")
        tokens.append((ta, tb))
        coros.append(get_cross_rate(ta, tb))

    results = await asyncio.gather(*coros, return_exceptions=True)

    for (ta, tb), res in zip(tokens, results):
        if isinstance(res, Exception):
            failed.append(f"{ta}/{tb} ❌ ({res})")
        else:
            add_watched_pair(ta, tb, res, user_id)          # ← user_id
            added.append(f"{ta}/{tb} ({res:.6f})")

    parts: List[str] = []
    if added:
        parts.append("✅ Додано:\n" + "\n".join(added))
    if failed:
        parts.append("❌ Не вдалося:\n" + "\n".join(failed))

    await update.message.reply_text("\n\n".join(parts) or "Нічого не додано.")


# ╭──────────────────────────────────────────────────────────╮
# │ ⚙️ Callback-кнопки Auto / Manual                         │
# ╰──────────────────────────────────────────────────────────╯
async def handle_crossrate_choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    q = update.callback_query
    await q.answer()

    tok_a, tok_b, uid = context.user_data["pair"]

    if q.data == "auto":
        try:
            rate = await get_cross_rate(tok_a, tok_b)
            add_watched_pair(tok_a, tok_b, rate, uid)      # ← user_id
            await q.edit_message_text(
                f"✅ Додано {tok_a}/{tok_b} з курсом {rate:.6f}"
            )
        except Exception as e:
            await q.edit_message_text(f"❌ Помилка: {e}")
        return await _finish(update, context)

    if q.data == "manual":
        await q.edit_message_text(f"✍️ Введіть курс для {tok_a}/{tok_b}:")
        return AWAITING_MANUAL_CROSSRATE

    await q.edit_message_text("⚠️ Невідома команда.")
    return await _finish(update, context)


# ╭──────────────────────────────────────────────────────────╮
# │ ✍️ Ручне введення                                        │
# ╰──────────────────────────────────────────────────────────╯
async def handle_manual_crossrate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    tok_a, tok_b, uid = context.user_data["pair"]

    try:
        rate = float(update.message.text.replace(",", "."))
        add_watched_pair(tok_a, tok_b, rate, uid)          # ← user_id
        await update.message.reply_text(
            f"✅ Додано {tok_a}/{tok_b} з курсом {rate}"
        )
        return await _finish(update, context)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Введіть числове значення курсу."
        )
        return AWAITING_MANUAL_CROSSRATE


# ╭──────────────────────────────────────────────────────────╮
# │ 🧹 Завершення сцени                                      │
# ╰──────────────────────────────────────────────────────────╯
async def _finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Видаляє службові повідомлення та завершує сцену."""
    chat_id = update.effective_chat.id
    await asyncio.gather(*[
        context.bot.delete_message(chat_id, mid)
        for mid in context.user_data.get("scene_messages", [])
    ], return_exceptions=True)

    context.user_data.clear()
    return ConversationHandler.END
