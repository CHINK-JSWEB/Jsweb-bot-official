import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                balance     REAL DEFAULT 0,
                created_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS orders (
                order_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                service_id  TEXT,
                link        TEXT,
                quantity    INTEGER,
                charge      REAL,
                panel_order_id TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS deposits (
                deposit_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                amount      REAL,
                proof_file_id TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  INTEGER,
                resolved_at INTEGER,
                resolved_by INTEGER
            );

            CREATE TABLE IF NOT EXISTS transactions (
                tx_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                type        TEXT,
                amount      REAL,
                note        TEXT,
                created_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS services_cache (
                service_id  TEXT PRIMARY KEY,
                name        TEXT,
                category    TEXT,
                rate        REAL,
                min_qty     INTEGER,
                max_qty     INTEGER,
                updated_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS service_map (
                panel_id    TEXT PRIMARY KEY,
                local_id    TEXT,
                name        TEXT,
                updated_at  INTEGER
            );

            CREATE TABLE IF NOT EXISTS dashboard_services (
                local_id    TEXT PRIMARY KEY,
                panel_id    TEXT,
                name        TEXT,
                provider    TEXT,
                price       REAL,
                updated_at  INTEGER
            );
            CREATE TABLE IF NOT EXISTS user_accounts (
                telegram_id TEXT PRIMARY KEY,
                site_username TEXT,
                site_password TEXT,
                linked_at   INTEGER
            );
            """
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── Users ─────────────────────────────────────────────────

def ensure_user(user_id: int, username: str | None):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, balance, created_at) "
            "VALUES (?, ?, 0, ?)",
            (user_id, username, int(time.time())),
        )
        conn.execute(
            "UPDATE users SET username = ? WHERE user_id = ?", (username, user_id)
        )


def get_balance(user_id: int) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT balance FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["balance"] if row else 0.0


def adjust_balance(user_id: int, amount: float, tx_type: str, note: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        conn.execute(
            "INSERT INTO transactions (user_id, type, amount, note, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, tx_type, amount, note, int(time.time())),
        )


def get_transactions(user_id: int, limit: int = 10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM transactions WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


# ── Deposits ──────────────────────────────────────────────

def create_deposit(user_id: int, amount: float, proof_file_id: str | None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO deposits (user_id, amount, proof_file_id, status, created_at) "
            "VALUES (?, ?, ?, 'pending', ?)",
            (user_id, amount, proof_file_id, int(time.time())),
        )
        return cur.lastrowid


def get_pending_deposits():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM deposits WHERE status = 'pending' ORDER BY created_at ASC"
        ).fetchall()


def get_deposit(deposit_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM deposits WHERE deposit_id = ?", (deposit_id,)
        ).fetchone()


def resolve_deposit(deposit_id: int, status: str, admin_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE deposits SET status = ?, resolved_at = ?, resolved_by = ? "
            "WHERE deposit_id = ?",
            (status, int(time.time()), admin_id, deposit_id),
        )


# ── Orders ────────────────────────────────────────────────

def create_order(user_id: int, service_id: str, link: str, quantity: int,
                  charge: float, panel_order_id: str | None, status: str = "pending") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO orders (user_id, service_id, link, quantity, charge, "
            "panel_order_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, service_id, link, quantity, charge, panel_order_id,
             status, int(time.time())),
        )
        return cur.lastrowid


def get_orders(user_id: int, limit: int = 10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def get_order(order_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()


def update_order_status(order_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id)
        )


# ── Services Cache (z-smm.com API) ──────────────────────────

def sync_services_cache(items: list[dict]):
    now = int(time.time())
    with get_conn() as conn:
        for s in items:
            conn.execute(
                "INSERT INTO services_cache (service_id, name, category, rate, "
                "min_qty, max_qty, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(service_id) DO UPDATE SET "
                "name=excluded.name, category=excluded.category, rate=excluded.rate, "
                "min_qty=excluded.min_qty, max_qty=excluded.max_qty, updated_at=excluded.updated_at",
                (
                    str(s.get("service")), s.get("name"), s.get("category"),
                    float(s.get("rate", 0)), int(float(s.get("min", 0))),
                    int(float(s.get("max", 0))), now,
                ),
            )


def get_cached_services(limit: int = 50):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM services_cache ORDER BY category, name LIMIT ?", (limit,)
        ).fetchall()


def get_cached_service(service_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM services_cache WHERE service_id = ?", (service_id,)
        ).fetchone()


def get_services_last_sync():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT MAX(updated_at) as t FROM services_cache"
        ).fetchone()
        return row["t"] if row and row["t"] else None


# ── Service ID Mapping (manual panel ID ↔ local ID) ─────────

def add_mapping(panel_id: str, local_id: str, name: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO service_map (panel_id, local_id, name, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(panel_id) DO UPDATE SET local_id=excluded.local_id, "
            "name=excluded.name, updated_at=excluded.updated_at",
            (panel_id, local_id, name, int(time.time())),
        )


def get_local_id(panel_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM service_map WHERE panel_id = ?", (panel_id,)
        ).fetchone()
        return row


def list_mappings(limit: int = 50):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM service_map ORDER BY CAST(panel_id AS INTEGER) LIMIT ?",
            (limit,),
        ).fetchall()


# ── Dashboard Services (scraped from jsweboosting.site admin) ──

def sync_dashboard_services(rows: list[dict]):
    now = int(time.time())
    with get_conn() as conn:
        for r in rows:
            conn.execute(
                "INSERT INTO dashboard_services (local_id, panel_id, name, provider, price, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(local_id) DO UPDATE SET "
                "panel_id=excluded.panel_id, name=excluded.name, provider=excluded.provider, "
                "price=excluded.price, updated_at=excluded.updated_at",
                (r["local_id"], r["panel_id"], r["name"], r["provider"], r["price"], now),
            )


def find_dashboard_by_panel_id(panel_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dashboard_services WHERE panel_id = ?", (panel_id,)
        ).fetchone()


def search_dashboard_services(keyword: str, limit: int = 15):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dashboard_services WHERE name LIKE ? LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()


def dashboard_services_count():
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM dashboard_services").fetchone()
        return row["c"] if row else 0


def dashboard_last_sync():
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(updated_at) as t FROM dashboard_services").fetchone()
        return row["t"] if row and row["t"] else None
# ── User/Booster Site Accounts ──────────────────────────────

def save_user_account(telegram_id: int, username: str, password: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO user_accounts (telegram_id, site_username, site_password, linked_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET "
            "site_username=excluded.site_username, site_password=excluded.site_password, "
            "linked_at=excluded.linked_at",
            (str(telegram_id), username, password, int(time.time())),
        )


def get_user_account(telegram_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM user_accounts WHERE telegram_id = ?", (str(telegram_id),)
        ).fetchone()


def delete_user_account(telegram_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_accounts WHERE telegram_id = ?", (str(telegram_id),))
        
def get_dashboard_service(local_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM dashboard_services WHERE local_id = ?", (local_id,)
        ).fetchone()
        
def get_all_user_accounts():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM user_accounts").fetchall()