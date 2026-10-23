"""
src/database.py
---------------
SQLite persistence layer for Mezy Action Tracker.

Provides parameterized CRUD operations, schema initialization, validation,
and transaction safety for improvement actions.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from config.settings import DB_PATH

VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_STATUSES = {"Open", "In Progress", "Resolved"}


def get_db_connection(db_path: Optional[Union[Path, str]] = None) -> sqlite3.Connection:
    """Return a connection to the SQLite database with Row factory enabled."""
    target_path = Path(db_path) if db_path else DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Union[Path, str]] = None) -> None:
    """Initialize the SQLite database schema if not already present."""
    target_path = Path(db_path) if db_path else DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection(target_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    evidence TEXT DEFAULT '',
                    action TEXT NOT NULL,
                    priority TEXT NOT NULL CHECK(priority IN ('High', 'Medium', 'Low')),
                    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'In Progress', 'Resolved')),
                    notes TEXT DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cursor = conn.execute("PRAGMA table_info(actions)")
            col_names = [row["name"] for row in cursor.fetchall()]
            if "source" not in col_names:
                conn.execute(
                    "ALTER TABLE actions ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';"
                )

            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_actions_priority ON actions(priority);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_actions_source ON actions(source);"
            )
    finally:
        conn.close()


def _normalize_priority(priority: str) -> str:
    p_norm = str(priority).strip().capitalize()
    if p_norm not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid priority '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"
        )
    return p_norm


def _normalize_status(status: str) -> str:
    s_clean = str(status).strip()
    # Normalize common variations
    norm_map = {
        "open": "Open",
        "in progress": "In Progress",
        "inprogress": "In Progress",
        "in_progress": "In Progress",
        "resolved": "Resolved",
        "closed": "Resolved",
        "done": "Resolved",
    }
    s_norm = norm_map.get(s_clean.lower(), s_clean)
    if s_norm not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}"
        )
    return s_norm


def create_action(
    title: str,
    action: str,
    priority: str = "Medium",
    evidence: str = "",
    notes: str = "",
    status: str = "Open",
    db_path: Optional[Union[Path, str]] = None,
    source: str = "manual",
) -> int:
    """Create a new action record with validated inputs and parameterized SQL."""
    init_db(db_path)
    t_clean = str(title).strip()
    a_clean = str(action).strip()

    if not t_clean:
        raise ValueError("Issue title is required and cannot be empty.")
    if not a_clean:
        raise ValueError("Suggested action is required and cannot be empty.")

    p_valid = _normalize_priority(priority)
    s_valid = _normalize_status(status)
    e_clean = str(evidence or "").strip()
    n_clean = str(notes or "").strip()
    src_clean = str(source or "manual").strip()

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO actions (title, evidence, action, priority, status, notes, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (t_clean, e_clean, a_clean, p_valid, s_valid, n_clean, src_clean),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def clear_ai_recommendation_actions(db_path: Optional[Union[Path, str]] = None) -> int:
    """
    Remove actions added from AI recommendations (source = 'ai_recommendation'),
    while strictly preserving user-created manual actions (source = 'manual').
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM actions WHERE source = 'ai_recommendation'"
            )
            return cursor.rowcount
    finally:
        conn.close()


def action_exists(
    title: str,
    action: str = "",
    db_path: Optional[Union[Path, str]] = None,
) -> bool:
    """Check if an action with identical title or action text already exists in SQLite."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        t_clean = str(title).strip().lower()
        a_clean = str(action).strip().lower() if action else ""
        if a_clean:
            cursor = conn.execute(
                "SELECT id FROM actions WHERE LOWER(TRIM(title)) = ? OR LOWER(TRIM(action)) = ? LIMIT 1",
                (t_clean, a_clean),
            )
        else:
            cursor = conn.execute(
                "SELECT id FROM actions WHERE LOWER(TRIM(title)) = ? LIMIT 1",
                (t_clean,),
            )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def get_all_actions(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: Optional[Union[Path, str]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve all actions matching optional status, priority, and text search filters."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        query = "SELECT * FROM actions WHERE 1=1"
        params: List[Any] = []

        if status and status != "All":
            norm_s = _normalize_status(status)
            query += " AND status = ?"
            params.append(norm_s)

        if priority and priority != "All":
            norm_p = _normalize_priority(priority)
            query += " AND priority = ?"
            params.append(norm_p)

        if search_query and search_query.strip():
            like_val = f"%{search_query.strip()}%"
            query += " AND (title LIKE ? OR action LIKE ? OR evidence LIKE ? OR notes LIKE ?)"
            params.extend([like_val, like_val, like_val, like_val])

        query += " ORDER BY id DESC"

        cursor = conn.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_action_by_id(
    action_id: int, db_path: Optional[Union[Path, str]] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve a single action by its unique primary key ID."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM actions WHERE id = ?", (int(action_id),)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_action(
    action_id: int,
    title: str,
    action: str,
    priority: str,
    status: str,
    evidence: str = "",
    notes: str = "",
    db_path: Optional[Union[Path, str]] = None,
) -> bool:
    """Update all fields of an existing action using parameterized SQL."""
    init_db(db_path)
    t_clean = str(title).strip()
    a_clean = str(action).strip()

    if not t_clean:
        raise ValueError("Issue title is required and cannot be empty.")
    if not a_clean:
        raise ValueError("Suggested action is required and cannot be empty.")

    p_valid = _normalize_priority(priority)
    s_valid = _normalize_status(status)
    e_clean = str(evidence or "").strip()
    n_clean = str(notes or "").strip()

    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                UPDATE actions
                SET title = ?, action = ?, priority = ?, status = ?, evidence = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (t_clean, a_clean, p_valid, s_valid, e_clean, n_clean, int(action_id)),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def update_action_status_and_notes(
    action_id: int,
    status: str,
    notes: Optional[str] = None,
    db_path: Optional[Union[Path, str]] = None,
) -> bool:
    """Quickly update the status and optionally the notes of an action."""
    init_db(db_path)
    s_valid = _normalize_status(status)
    conn = get_db_connection(db_path)
    try:
        with conn:
            if notes is not None:
                cursor = conn.execute(
                    """
                    UPDATE actions
                    SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (s_valid, str(notes).strip(), int(action_id)),
                )
            else:
                cursor = conn.execute(
                    """
                    UPDATE actions
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (s_valid, int(action_id)),
                )
            return cursor.rowcount > 0
    finally:
        conn.close()


def delete_action(
    action_id: int, db_path: Optional[Union[Path, str]] = None
) -> bool:
    """Delete an action record by ID."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "DELETE FROM actions WHERE id = ?", (int(action_id),)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def get_action_statistics(
    db_path: Optional[Union[Path, str]] = None,
) -> Dict[str, int]:
    """Return aggregated counts of actions by status and priority."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open_cnt,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_prog_cnt,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_cnt,
                SUM(CASE WHEN priority = 'High' THEN 1 ELSE 0 END) AS high_cnt
            FROM actions
            """
        )
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "open": row["open_cnt"] or 0,
            "in_progress": row["in_prog_cnt"] or 0,
            "resolved": row["resolved_cnt"] or 0,
            "high_priority": row["high_cnt"] or 0,
        }
    finally:
        conn.close()
