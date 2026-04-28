import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


DB_PATH = Path("data") / "trackers.db"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def ensure_data_dir() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    ensure_data_dir()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(get_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trackers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_url TEXT NOT NULL,
                target_price REAL NOT NULL,
                recipient_email TEXT NOT NULL,
                interval_hours INTEGER NOT NULL DEFAULT 6,
                current_price REAL,
                last_title TEXT,
                last_status TEXT NOT NULL DEFAULT 'Pending first check',
                last_error TEXT,
                last_checked_at TEXT,
                next_check_at TEXT,
                last_alerted_at TEXT,
                last_alerted_price REAL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def list_trackers() -> list[sqlite3.Row]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            "SELECT * FROM trackers ORDER BY created_at DESC"
        ).fetchall()
    return list(rows)


def create_tracker(
    product_url: str,
    target_price: float,
    recipient_email: str,
    interval_hours: int,
) -> int:
    created_at = utc_now_iso()
    next_check_at = created_at
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO trackers (
                product_url,
                target_price,
                recipient_email,
                interval_hours,
                last_status,
                next_check_at,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_url,
                target_price,
                recipient_email,
                interval_hours,
                "Queued for first check",
                next_check_at,
                created_at,
            ),
        )
        connection.commit()
    return int(cursor.lastrowid)


def get_tracker(tracker_id: int) -> sqlite3.Row | None:
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT * FROM trackers WHERE id = ?",
            (tracker_id,),
        ).fetchone()
    return row


def delete_tracker(tracker_id: int) -> None:
    with closing(get_connection()) as connection:
        connection.execute("DELETE FROM trackers WHERE id = ?", (tracker_id,))
        connection.commit()


def update_success(
    tracker_id: int,
    *,
    title: str,
    current_price: float,
    status: str,
    interval_hours: int,
    alerted: bool,
) -> None:
    checked_at = utc_now()
    next_check_at = checked_at + timedelta(hours=interval_hours)
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE trackers
            SET current_price = ?,
                last_title = ?,
                last_status = ?,
                last_error = NULL,
                last_checked_at = ?,
                next_check_at = ?,
                last_alerted_at = CASE WHEN ? THEN ? ELSE last_alerted_at END,
                last_alerted_price = CASE WHEN ? THEN ? ELSE last_alerted_price END
            WHERE id = ?
            """,
            (
                current_price,
                title,
                status,
                checked_at.isoformat(),
                next_check_at.isoformat(),
                1 if alerted else 0,
                checked_at.isoformat(),
                1 if alerted else 0,
                current_price,
                tracker_id,
            ),
        )
        connection.commit()


def update_error(tracker_id: int, *, error_message: str, interval_hours: int) -> None:
    checked_at = utc_now()
    next_check_at = checked_at + timedelta(hours=interval_hours)
    with closing(get_connection()) as connection:
        connection.execute(
            """
            UPDATE trackers
            SET last_status = ?,
                last_error = ?,
                last_checked_at = ?,
                next_check_at = ?
            WHERE id = ?
            """,
            (
                "Check failed",
                error_message,
                checked_at.isoformat(),
                next_check_at.isoformat(),
                tracker_id,
            ),
        )
        connection.commit()


def due_trackers() -> list[sqlite3.Row]:
    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM trackers
            WHERE next_check_at IS NULL
               OR next_check_at <= ?
            ORDER BY next_check_at ASC, created_at ASC
            """,
            (utc_now_iso(),),
        ).fetchall()
    return list(rows)

