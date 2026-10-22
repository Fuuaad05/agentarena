import json
import sqlite3

from pathlib import Path
from datetime import datetime, timezone


DATABASE_PATH = Path("agentarena.db")


def get_connection():
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence_score REAL,
                bug_report TEXT NOT NULL,
                report_json TEXT NOT NULL
            )
            """
        )

        connection.commit()


def save_investigation(report: dict) -> int:
    initialize_database()

    created_at = report.get(
        "timestamp",
        datetime.now(timezone.utc).isoformat(),
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO investigations (
                created_at,
                status,
                evidence_score,
                bug_report,
                report_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at,
                report.get("status", "INCONCLUSIVE"),
                report.get("evidence_score"),
                report.get("bug_report", ""),
                json.dumps(report),
            ),
        )

        connection.commit()

        return int(cursor.lastrowid)


def list_investigations(limit: int = 50):
    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                status,
                evidence_score,
                bug_report
            FROM investigations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [dict(row) for row in rows]


def get_investigation(investigation_id: int):
    initialize_database()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT report_json
            FROM investigations
            WHERE id = ?
            """,
            (investigation_id,),
        ).fetchone()

        if row is None:
            return None

        return json.loads(row["report_json"])