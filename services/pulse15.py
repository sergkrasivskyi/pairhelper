"""
15-хв «пульс»

• Записує крос-курс у cross_rate_history
• Надсилає пуш, якщо |Δ30m| ≥ SIGNIFICANT
"""

from __future__ import annotations
import asyncio, os, datetime as dt, sqlite3
from typing import Optional
from telegram import Bot
from telegram.ext import Application

from services.pair_storage import get_all_pairs
from services.cross_rate   import get_cross_rate   # async
# ------------------------------------------------------------
DB            = "db/monitoring.db"
SIGNIFICANT   = 0.3          # % поріг push-нотифікації
# ------------------------------------------------------------
def store_tick(pair_id: int, rate: float, ts: str) -> None:
    with sqlite3.connect(DB) as c:
        c.execute(
            "INSERT INTO cross_rate_history (pair_id, rate, ts) VALUES (?,?,?)",
            (pair_id, rate, ts)
        )

def last_rate(pair_id: int) -> Optional[float]:
    """Останній записаний крос-курс із БД (None, якщо ще немає)."""
    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT rate FROM cross_rate_history "
            "WHERE pair_id=? ORDER BY id DESC LIMIT 1",
            (pair_id,)
        ).fetchone()
    return row[0] if row else None

def pct_change(new: float, old: float) -> float:
    return (new - old) / old * 100 if old else 0.0

def last_delta_percent(pair_id: int, ticks: int = 2) -> float:
    """%-зміна між новим і N-м попереднім тиком (ticks=2 ≅ 30 хв)."""
    with sqlite3.connect(DB) as c:
        rows = c.execute(
            "SELECT rate FROM cross_rate_history "
            "WHERE pair_id=? ORDER BY id DESC LIMIT ?",
            (pair_id, ticks)
        ).fetchall()
    if len(rows) < ticks:
        return 0.0
    newest, oldest = rows[0][0], rows[-1][0]
    return pct_change(newest, oldest)
# ------------------------------------------------------------
async def _get_bot(passed: Optional[Bot] = None) -> Bot:
    if passed:
        return passed
    try:
        return Application.get_current().bot
    except RuntimeError:
        return Bot(os.getenv("BOT_TOKEN"))
# ------------------------------------------------------------
async def pulse(bot: Bot | None = None) -> None:
    bot   = await _get_bot(bot)
    pairs = get_all_pairs()
    if not pairs:
        return

    coros  = [get_cross_rate(p["token_a"], p["token_b"]) for p in pairs]
    rates  = await asyncio.gather(*coros, return_exceptions=True)
    now_ts = dt.datetime.utcnow().isoformat()

    for p, r in zip(pairs, rates):
        if isinstance(r, Exception):
            continue                      # API-помилка

        prev = last_rate(p["id"])
        if prev is not None and r == prev:    # ціна не змінилась → пропускаємо
            continue

        store_tick(p["id"], r, now_ts)

        delta30 = last_delta_percent(p["id"], 2)
        if abs(delta30) < SIGNIFICANT:
            continue                         # дрібний рух — мовчимо

        delta_start = pct_change(r, p["start_rate"])
        flag        = "🟢" if p["trade_open"] else "⚪️"

        msg = (
            f"{flag} {p['token_a']}/{p['token_b']}  {r:.6f}\n"
            f"  від старту: {delta_start:+.2f}%\n"
            f"  за 30 хв:   {delta30:+.2f}%"
        )
        await bot.send_message(chat_id=p["user_id"], text=msg)
