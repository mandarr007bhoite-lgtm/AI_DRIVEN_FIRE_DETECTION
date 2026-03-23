import sqlite3
from typing import List, Tuple, Dict, Any

DB_NAME = "users.db"


def _get_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_schema() -> None:
    conn = _get_connection()
    cursor = conn.cursor()

    # Ensure users table exists (mirror existing app expectations)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    # Ensure detection_history exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            date TEXT,
            time TEXT,
            intensity TEXT,
            seconds_ago INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # For existing DBs created without seconds_ago, add it conditionally
    cursor.execute("PRAGMA table_info(detection_history)")
    columns = [row[1] for row in cursor.fetchall()]
    if "seconds_ago" not in columns:
        cursor.execute("ALTER TABLE detection_history ADD COLUMN seconds_ago INTEGER")

    # Web push subscriptions table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endpoint TEXT UNIQUE NOT NULL,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


def save_detection(day: str, date: str, time_str: str, intensity: str, seconds_ago: int) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO detection_history (day, date, time, intensity, seconds_ago)
        VALUES (?, ?, ?, ?, ?)
        """,
        (day, date, time_str, intensity, seconds_ago),
    )
    conn.commit()
    conn.close()


def fetch_history_rows() -> List[Tuple[Any, ...]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT day, date, time, intensity, created_at, seconds_ago FROM detection_history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def save_push_subscription(endpoint: str, p256dh: str, auth: str) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO push_subscriptions (endpoint, p256dh, auth) VALUES (?, ?, ?)
        """,
        (endpoint, p256dh, auth),
    )
    conn.commit()
    conn.close()


def fetch_push_subscriptions() -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT endpoint, p256dh, auth FROM push_subscriptions")
    rows = cursor.fetchall()
    conn.close()
    return [{"endpoint": r[0], "p256dh": r[1], "auth": r[2]} for r in rows]


def fetch_latest_detection() -> Dict[str, Any]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT day, date, time, intensity, created_at FROM detection_history ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {}
    return {"day": row[0], "date": row[1], "time": row[2], "intensity": row[3], "created_at": row[4]}


