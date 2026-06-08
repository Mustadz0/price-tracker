import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DB_PATH = Path(__file__).parent.parent / "data" / "prices.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init(conn)
    return conn


def _init(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            name TEXT,
            currency TEXT DEFAULT 'USD',
            alert_threshold REAL DEFAULT -5.0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            checked_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE TABLE IF NOT EXISTS price_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price REAL,
            new_price REAL,
            change_pct REAL,
            message TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)


class PriceDB:
    def __init__(self):
        self.conn = get_db()

    def add_product(self, url: str, name: str = "") -> int:
        try:
            cur = self.conn.execute(
                "INSERT INTO products (url, name) VALUES (?, ?)",
                (url, name or url),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            row = self.conn.execute(
                "SELECT id FROM products WHERE url = ?", (url,)
            ).fetchone()
            return row["id"] if row else 0

    def get_products(self) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC"
        ).fetchall()

    def get_product(self, pid: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM products WHERE id = ?", (pid,)
        ).fetchone()

    def save_price(self, product_id: int, price: float, currency: str = "USD"):
        self.conn.execute(
            "INSERT INTO price_history (product_id, price, currency) VALUES (?, ?, ?)",
            (product_id, price, currency),
        )
        self.conn.commit()

    def get_latest_price(self, product_id: int) -> Optional[float]:
        row = self.conn.execute(
            "SELECT price FROM price_history WHERE product_id = ? ORDER BY checked_at DESC LIMIT 1",
            (product_id,),
        ).fetchone()
        return row["price"] if row else None

    def get_previous_price(self, product_id: int) -> Optional[float]:
        row = self.conn.execute(
            "SELECT price FROM price_history WHERE product_id = ? ORDER BY checked_at DESC LIMIT 1 OFFSET 1",
            (product_id,),
        ).fetchone()
        return row["price"] if row else None

    def get_price_history(self, product_id: int, limit: int = 30) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM price_history WHERE product_id = ? ORDER BY checked_at DESC LIMIT ?",
            (product_id, limit),
        ).fetchall()

    def record_alert(self, product_id: int, old_price: float, new_price: float, change_pct: float, message: str):
        self.conn.execute(
            "INSERT INTO price_alerts (product_id, old_price, new_price, change_pct, message) VALUES (?, ?, ?, ?, ?)",
            (product_id, old_price, new_price, change_pct, message),
        )
        self.conn.commit()

    def get_alerts(self, limit: int = 20) -> List[sqlite3.Row]:
        return self.conn.execute(
            """SELECT a.*, p.name as product_name, p.url 
               FROM price_alerts a JOIN products p ON a.product_id = p.id 
               ORDER BY a.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()

    def delete_product(self, pid: int):
        self.conn.execute("DELETE FROM price_history WHERE product_id = ?", (pid,))
        self.conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        self.conn.commit()

    def close(self):
        self.conn.close()
