import sqlite3
from datetime import datetime
import logging

DB_PATH = "db/monitoring.db"

# Налаштування логування (додаємо, якщо не ініціалізовано)
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(
        filename="bot.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def add_watched_pair(token_a: str, token_b: str, cross_rate: float):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS watched_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_a TEXT,
            token_b TEXT,
            cross_rate REAL,
            created_at TEXT
        )
    """)

    c.execute("""
        INSERT INTO watched_pairs (token_a, token_b, cross_rate, created_at)
        VALUES (?, ?, ?, ?)
    """, (token_a, token_b, cross_rate, datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()


def get_all_pairs():
    """Повертає всі пари у вигляді списку словників."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, token_a, token_b, cross_rate, created_at FROM watched_pairs")
    rows = c.fetchall()
    conn.close()

    logger.info(f"🔍 Отримано {len(rows)} пар(и) з БД")

    return [
        {
            "id": row[0],
            "token_a": row[1],
            "token_b": row[2],
            "cross_rate": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def delete_pair_by_id(pair_id: int):
    """Видаляє пару по ID."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM watched_pairs WHERE id = ?", (pair_id,))
    conn.commit()
    conn.close()
