import sqlite3

def init_db():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watched_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_a TEXT,
            token_b TEXT,
            start_cross_rate REAL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_watched_pair(token_a, token_b, cross_rate):
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO watched_pairs (token_a, token_b, start_cross_rate)
        VALUES (?, ?, ?)
    ''', (token_a.upper(), token_b.upper(), cross_rate))
    conn.commit()
    conn.close()
