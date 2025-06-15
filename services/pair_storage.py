"""
Робота з локальною SQLite-БД «monitoring.db».

* таблиця **watched_pairs** — активні пари, один рядок = одна пара
* таблиця **cross_rate_history** — 15-хв тіки (створюється в pulse15)
"""

from __future__ import annotations
import sqlite3, logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = "db/monitoring.db"

# ──────────────────────────────
# Логер
# ──────────────────────────────
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        filename="bot.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

# ──────────────────────────────
# ІНІЦІАЛІЗАЦІЯ/МІГРАЦІЯ
# ──────────────────────────────
def _ensure_tables() -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS watched_pairs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                token_a       TEXT,
                token_b       TEXT,
                start_rate    REAL,
                start_ts      TEXT,
                user_id       INTEGER,
                potential_move REAL      DEFAULT NULL,
                trade_open    INTEGER    DEFAULT 0
            )
        """)
        # історію створюємо «на всяк випадок», щоб не падали insert’и
        c.execute("""
            CREATE TABLE IF NOT EXISTS cross_rate_history (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id INTEGER,
                rate    REAL,
                ts      TEXT
            )
        """)

_ensure_tables()

# ──────────────────────────────
# CRUD-операції
# ──────────────────────────────
def add_watched_pair(
    token_a: str,
    token_b: str,
    start_rate: float,
    user_id: int
) -> None:
    """Додає пару в моніторинг."""
    ts = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            INSERT INTO watched_pairs
              (token_a, token_b, start_rate, start_ts, user_id)
            VALUES (?,?,?,?,?)
        """, (token_a, token_b, start_rate, ts, user_id))
    logger.info(f"➕ Added {token_a}/{token_b} @ {start_rate} for user {user_id}")


def get_all_pairs() -> List[Dict[str, Any]]:
    """Повертає всі пари списком словників."""
    with sqlite3.connect(DB_PATH) as c:
        rows = c.execute("""
            SELECT id, token_a, token_b, start_rate, start_ts,
                   user_id, potential_move, trade_open
            FROM watched_pairs
            ORDER BY id
        """).fetchall()

    res = [{
        "id": row[0],
        "token_a": row[1],
        "token_b": row[2],
        "start_rate": row[3],
        "start_ts": row[4],
        "user_id": row[5],
        "potential_move": row[6],
        "trade_open": bool(row[7]),
    } for row in rows]

    logger.info(f"🔍 Отримано {len(res)} пар(и) з БД")
    return res


def get_pair(pair_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB_PATH) as c:
        row = c.execute("""
            SELECT id, token_a, token_b, start_rate, start_ts,
                   user_id, potential_move, trade_open
            FROM watched_pairs WHERE id = ?
        """, (pair_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "token_a": row[1],
        "token_b": row[2],
        "start_rate": row[3],
        "start_ts": row[4],
        "user_id": row[5],
        "potential_move": row[6],
        "trade_open": bool(row[7]),
    }


def delete_pair_by_id(pair_id: int) -> None:
    with sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM watched_pairs WHERE id=?", (pair_id,))
    logger.info(f"🗑 Deleted pair id={pair_id}")


def toggle_trade(pair_id: int, state: bool) -> None:
    """Позначити/зняти «угода відкрита»."""
    with sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE watched_pairs SET trade_open=? WHERE id=?",
                  (int(state), pair_id))
    logger.info(f"🔔 trade_open={state} for id={pair_id}")


def set_potential(pair_id: int, value: Optional[float]) -> None:
    """Задати (або скинути) потенціал руху %."""
    with sqlite3.connect(DB_PATH) as c:
        c.execute("UPDATE watched_pairs SET potential_move=? WHERE id=?",
                  (value, pair_id))
    logger.info(f"🎯 potential_move={value} for id={pair_id}")
