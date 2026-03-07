import sqlite3
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from pathlib import Path
DB_PATH = Path(__file__).parent / "resources.db"


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def _add_column_if_missing(cursor, table: str, column: str, coltype: str):
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall()]
    if column not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        url TEXT,
        title TEXT,
        raw_input TEXT,
        raw_data TEXT,
        cleaned_data TEXT,
        llm_output TEXT,
        files TEXT,
        status TEXT,
        error TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_resources_source ON resources(source)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_resources_created_at ON resources(created_at)
    """)

    _add_column_if_missing(cursor, "resources", "vault_title",   "TEXT")
    _add_column_if_missing(cursor, "resources", "vault_snippet", "TEXT")
    _add_column_if_missing(cursor, "resources", "session_id", "INTEGER")

    conn.commit()
    conn.close()


def save_resource(
    source,
    url,
    title=None,
    raw_input=None,
    raw_data=None,
    cleaned_data=None,
    llm_output=None,
    files=None,
    status="processed",
    error=None,
    vault_title=None,
    vault_snippet=None,
    session_id=None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO resources
            (source, url, title, raw_input, raw_data, cleaned_data,
            llm_output, files, status, error, created_at, vault_title, vault_snippet, session_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                source,
                url,
                title,
                json.dumps(raw_input, ensure_ascii=False) if isinstance(raw_input, dict) else raw_input,
                json.dumps(raw_data,  ensure_ascii=False) if isinstance(raw_data,  dict) else raw_data,
                json.dumps(cleaned_data, ensure_ascii=False) if isinstance(cleaned_data, dict) else cleaned_data,
                llm_output,
                json.dumps(files, ensure_ascii=False) if files else None,
                status,
                error,
                datetime.now(timezone.utc).isoformat(),
                vault_title,
                vault_snippet,
                session_id,
            ),
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"DB save failed: {e}")
    finally:
        conn.close()


def get_resources(limit=500):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
          id, source, url, title,
          raw_input, raw_data, cleaned_data, llm_output,
          files, status, error, created_at,
          vault_title, vault_snippet,
          session_id
        FROM resources
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_resource(resource_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
          id, source, url, title,
          raw_input, raw_data, cleaned_data, llm_output,
          files, status, error, created_at,
          vault_title, vault_snippet,
          session_id
        FROM resources
        WHERE id=?
        """,
        (resource_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def delete_resource(resource_id):
    """Hard-deletes a resource by id."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM resources WHERE id=?", (resource_id,))
    conn.commit()
    conn.close()

def update_resource_answer(resource_id: int, llm_output: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE resources SET llm_output=? WHERE id=?",
        (llm_output, resource_id)
    )
    conn.commit()
    conn.close()
