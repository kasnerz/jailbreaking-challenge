import json
import sqlite3
import time
from typing import Any, Dict, List

from .config import settings


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                success INTEGER NOT NULL,
                prompt_length INTEGER NOT NULL,
                ts INTEGER NOT NULL
            )
        """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                messages TEXT NOT NULL,
                success INTEGER NOT NULL,
                ts INTEGER NOT NULL
            )
        """
        )
        conn.commit()


def record_attempt(level: str, success: bool, prompt_length: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO attempts (level, success, prompt_length, ts) VALUES (?, ?, ?, ?)",
            (level, int(success), prompt_length, int(time.time())),
        )
        conn.commit()


def record_conversation(level: str, messages: List[Dict[str, Any]], success: bool):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO conversations (level, messages, success, ts) VALUES (?, ?, ?, ?)",
            (level, json.dumps(messages), int(success), int(time.time())),
        )
        conn.commit()


def get_stats() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                level,
                COUNT(*) AS attempts,
                SUM(success) AS successes
            FROM attempts
            GROUP BY level
            ORDER BY level
        """
        ).fetchall()

    result = []
    for row in rows:
        attempts = row["attempts"]
        successes = row["successes"] or 0
        rate = round(successes / attempts, 3) if attempts > 0 else 0.0
        result.append(
            {
                "level": row["level"],
                "attempts": attempts,
                "successes": successes,
                "rate": rate,
            }
        )
    return result
