"""
Щогодинний звіт по всіх парах.
• відкриті угоди показує першими;
• бере останній 15-хв тік з cross_rate_history;
• порівнює зі стартом і з останніми 30-ма хв.
"""

from __future__ import annotations
import os, sqlite3, datetime as dt
from typing import Optional
from telegram import Bot
from services.pair_storage import get_all_pairs
from services.pulse15 import last_delta_percent, pct_change

DB = "db/monitoring.db"


def last_rate(pair_id: int) -> Optional[float]:
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT rate FROM cross_rate_history "
            "WHERE pair_id=? ORDER BY id DESC LIMIT 1",
            (pair_id,),
        ).fetchone()
    return row[0] if row else None


async def hourly_report(bot: Bot | None = None):
    """
    Викликається APScheduler-ом раз на годину.
    Параметр *bot* передаємо з main.py, а якщо його нема — створюємо
    вручну по BOT_TOKEN.
    """
    if bot is None:
        try:
            # спроба взяти бота з поточного Application (якщо виклик з хендлера)
            from telegram.ext import Application

            bot = Application.get_current().bot
        except RuntimeError:
            # fallback — створити напряму
            bot = Bot(os.getenv("BOT_TOKEN"))

    pairs = get_all_pairs()
    if not pairs:
        return

    pairs.sort(key=lambda p: (p["trade_open"] == 0, p["id"]))  # відкриті угоди вгорі
    ts = dt.datetime.utcnow().strftime("%H:%M")
    header = f"🕛 Підсумок {ts} UTC"

    await bot.send_chat_action(chat_id=pairs[0]["user_id"], action="typing")

    lines = []
    for p in pairs:
        last = last_rate(p["id"])
        if last is None:
            continue

        pct_start = pct_change(last, p["start_rate"])
        pct_30m = last_delta_percent(p["id"], 2)

        line = (
            f"{'🟢' if p['trade_open'] else '⚪️'} "
            f"{p['token_a']}/{p['token_b']} {last:.6f}  "
            f"старт {pct_start:+.2f}% · 30 хв {pct_30m:+.2f}%"
        )
        if p["potential_move"] is not None:
            line += f" · 🎯 {p['potential_move']:+.1f}%"
        lines.append(line)

    await bot.send_message(
        chat_id=pairs[0]["user_id"],
        text=f"{header}\n" + "\n".join(lines),
        disable_notification=True,
    )
