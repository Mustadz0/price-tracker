import hashlib
import os
import secrets
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
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 0,
            url TEXT NOT NULL,
            name TEXT,
            currency TEXT DEFAULT 'USD',
            alert_threshold REAL DEFAULT -5.0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
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


def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
    if salt is None:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _check_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        return _hash_password(password, salt)[0] == stored
    except ValueError:
        return False


class PriceDB:
    def __init__(self):
        self.conn = get_db()

    def register_user(self, email: str, password: str, name: str = "") -> int:
        pw_hash = _hash_password(password)[0]
        try:
            cur = self.conn.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                (email, pw_hash, name or email.split("@")[0]),
            )
            self.conn.commit()
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return -1

    def login_user(self, email: str, password: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row and _check_password(password, row["password_hash"]):
            token = secrets.token_hex(32)
            self.conn.execute(
                "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
                (row["id"], token),
            )
            self.conn.commit()
            return token
        return None

    def get_user_by_token(self, token: str) -> Optional[sqlite3.Row]:
        row = self.conn.execute(
            """SELECT u.id, u.email, u.name FROM sessions s
               JOIN users u ON s.user_id = u.id
               WHERE s.token = ?""",
            (token,),
        ).fetchone()
        return row

    def logout(self, token: str):
        self.conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.conn.commit()

    def add_product(self, url: str, name: str = "", user_id: int = 0) -> int:
        existing = self.conn.execute(
            "SELECT id FROM products WHERE url = ? AND user_id = ?", (url, user_id)
        ).fetchone()
        if existing:
            return existing["id"]
        cur = self.conn.execute(
            "INSERT INTO products (url, name, user_id) VALUES (?, ?, ?)",
            (url, name or url, user_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_products(self, user_id: int = 0) -> List[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM products WHERE is_active = 1 AND user_id = ? ORDER BY created_at DESC",
            (user_id,),
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

    def get_alerts(self, user_id: int = 0, limit: int = 20) -> List[sqlite3.Row]:
        return self.conn.execute(
            """SELECT a.*, p.name as product_name, p.url
               FROM price_alerts a
               JOIN products p ON a.product_id = p.id
               WHERE p.user_id = ?
               ORDER BY a.created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()

    def delete_product(self, pid: int):
        self.conn.execute("DELETE FROM price_history WHERE product_id = ?", (pid,))
        self.conn.execute("DELETE FROM products WHERE id = ?", (pid,))
        self.conn.commit()

    def close(self):
        self.conn.close()
