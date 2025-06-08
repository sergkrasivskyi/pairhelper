import sqlite3
from datetime import datetime

DB_PATH = "db/monitoring.db"

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
