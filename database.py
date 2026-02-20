"""
Database module for My Planner application.
Supports both local SQLite and Turso (cloud SQLite) backends.
Automatically detects which to use based on Streamlit secrets or environment variables.
"""

import sqlite3
import os
import json
import requests as http_requests
from datetime import datetime, date, timedelta
from contextlib import contextmanager

# ─── Backend Detection ──────────────────────────────────────────────────────────

TURSO_URL = None
TURSO_AUTH_TOKEN = None
USE_TURSO = False

try:
    import streamlit as st
    if "turso" in st.secrets:
        TURSO_URL = st.secrets["turso"]["url"]
        TURSO_AUTH_TOKEN = st.secrets["turso"]["auth_token"]
        USE_TURSO = True
except Exception:
    pass

if not USE_TURSO:
    TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
    TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
    if TURSO_URL and TURSO_AUTH_TOKEN:
        USE_TURSO = True

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner.db")


# ─── DictRow - Consistent row access ───────────────────────────────────────────

class DictRow(dict):
    """dict subclass that supports both dict-key and attribute access (like sqlite3.Row)."""
    def __getitem__(self, key):
        return super().__getitem__(key)
    def keys(self):
        return super().keys()


# ─── Turso HTTP API Helper ──────────────────────────────────────────────────────

def _turso_api_url():
    url = TURSO_URL.rstrip("/")
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    if not url.startswith("https://"):
        url = "https://" + url
    if not url.endswith("/v2/pipeline"):
        url += "/v2/pipeline"
    return url


def _turso_execute(sql: str, params: list = None, fetch: str = "all"):
    if params is None:
        params = []

    api_params = []
    for p in params:
        if p is None:
            api_params.append({"type": "null"})
        elif isinstance(p, int):
            api_params.append({"type": "integer", "value": str(p)})
        elif isinstance(p, float):
            api_params.append({"type": "float", "value": p})
        elif isinstance(p, str):
            api_params.append({"type": "text", "value": p})
        else:
            api_params.append({"type": "text", "value": str(p)})

    body = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": api_params}},
            {"type": "close"}
        ]
    }
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

    resp = http_requests.post(_turso_api_url(), json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    result = data.get("results", [{}])[0]
    if result.get("type") == "error":
        raise Exception(f"Turso error: {result['error']['message']}")

    response = result.get("response", {})
    res = response.get("result", {})

    if fetch == "lastrowid":
        return res.get("last_insert_rowid", 0)
    if fetch == "none":
        return None

    cols = [c["name"] for c in res.get("cols", [])]
    rows_data = res.get("rows", [])
    rows = []
    for row in rows_data:
        row_dict = DictRow()
        for i, col in enumerate(cols):
            val = row[i]
            if isinstance(val, dict):
                if val.get("type") == "integer" and val.get("value") is not None:
                    try:
                        row_dict[col] = int(val["value"])
                    except (ValueError, TypeError):
                        row_dict[col] = val.get("value")
                elif val.get("type") == "float" and val.get("value") is not None:
                    try:
                        row_dict[col] = float(val["value"])
                    except (ValueError, TypeError):
                        row_dict[col] = val.get("value")
                elif val.get("type") == "null":
                    row_dict[col] = None
                else:
                    row_dict[col] = val.get("value")
            else:
                row_dict[col] = val
        rows.append(row_dict)

    if fetch == "one":
        return rows[0] if rows else None
    return rows


def _turso_executescript(sql_script: str):
    statements = [s.strip() for s in sql_script.split(";") if s.strip()]
    reqs = [{"type": "execute", "stmt": {"sql": stmt}} for stmt in statements]
    reqs.append({"type": "close"})

    body = {"requests": reqs}
    headers = {
        "Authorization": f"Bearer {TURSO_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    resp = http_requests.post(_turso_api_url(), json=body, headers=headers, timeout=30)
    resp.raise_for_status()


# ─── Local SQLite Connection ────────────────────────────────────────────────────

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        color TEXT DEFAULT '#4A90D9',
        icon TEXT DEFAULT '📁',
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, name)
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'active',
        priority INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS subtasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        is_done INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS time_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        subtask_id INTEGER,
        duration_minutes REAL NOT NULL,
        log_date DATE NOT NULL,
        note TEXT DEFAULT '',
        source TEXT DEFAULT 'manual',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        FOREIGN KEY (subtask_id) REFERENCES subtasks(id) ON DELETE SET NULL
    );
    CREATE INDEX IF NOT EXISTS idx_time_logs_date ON time_logs(log_date);
    CREATE INDEX IF NOT EXISTS idx_time_logs_user ON time_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category_id);
"""


def init_db():
    if USE_TURSO:
        _turso_executescript(SCHEMA_SQL)
    else:
        with get_connection() as conn:
            conn.executescript(SCHEMA_SQL)


# ─── Universal Query Executor ──────────────────────────────────────────────────

def _query(sql: str, params: list = None, fetch: str = "all"):
    if params is None:
        params = []
    if USE_TURSO:
        return _turso_execute(sql, params, fetch)
    else:
        with get_connection() as conn:
            cursor = conn.execute(sql, params)
            if fetch == "lastrowid":
                return cursor.lastrowid
            elif fetch == "one":
                row = cursor.fetchone()
                if row is None:
                    return None
                return DictRow({key: row[key] for key in row.keys()})
            elif fetch == "all":
                rows = cursor.fetchall()
                return [DictRow({key: r[key] for key in r.keys()}) for r in rows]
            return None


# ─── User Operations ───────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, display_name: str = None) -> int:
    return _query(
        "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
        [username, password_hash, display_name or username], fetch="lastrowid"
    )


def get_user_by_username(username: str):
    return _query("SELECT * FROM users WHERE username = ?", [username], fetch="one")


# ─── Category Operations ───────────────────────────────────────────────────────

def get_categories(user_id: int):
    return _query(
        "SELECT * FROM categories WHERE user_id = ? ORDER BY sort_order, name", [user_id]
    )


def create_category(user_id: int, name: str, color: str = "#4A90D9", icon: str = "📁"):
    return _query(
        "INSERT INTO categories (user_id, name, color, icon) VALUES (?, ?, ?, ?)",
        [user_id, name, color, icon], fetch="lastrowid"
    )


def update_category(cat_id: int, name: str = None, color: str = None, icon: str = None):
    if name:
        _query("UPDATE categories SET name = ? WHERE id = ?", [name, cat_id], fetch="none")
    if color:
        _query("UPDATE categories SET color = ? WHERE id = ?", [color, cat_id], fetch="none")
    if icon:
        _query("UPDATE categories SET icon = ? WHERE id = ?", [icon, cat_id], fetch="none")


def delete_category(cat_id: int):
    _query("DELETE FROM categories WHERE id = ?", [cat_id], fetch="none")


# ─── Task Operations ───────────────────────────────────────────────────────────

def get_tasks(user_id: int, category_id: int = None, status: str = None):
    query = """SELECT t.*, c.name as category_name, c.color as category_color,
               c.icon as category_icon FROM tasks t
               JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"""
    params = [user_id]
    if category_id:
        query += " AND t.category_id = ?"
        params.append(category_id)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    query += " ORDER BY t.sort_order, t.created_at DESC"
    return _query(query, params)


def create_task(user_id: int, category_id: int, title: str, description: str = ""):
    return _query(
        "INSERT INTO tasks (user_id, category_id, title, description) VALUES (?, ?, ?, ?)",
        [user_id, category_id, title, description], fetch="lastrowid"
    )


def update_task(task_id: int, **kwargs):
    allowed = {'title', 'description', 'status', 'priority', 'category_id', 'sort_order'}
    for key, val in kwargs.items():
        if key in allowed and val is not None:
            _query(f"UPDATE tasks SET {key} = ? WHERE id = ?", [val, task_id], fetch="none")
    if kwargs.get('status') == 'completed':
        _query("UPDATE tasks SET completed_at = ? WHERE id = ?",
               [datetime.now().isoformat(), task_id], fetch="none")


def delete_task(task_id: int):
    _query("DELETE FROM tasks WHERE id = ?", [task_id], fetch="none")


# ─── Subtask Operations ────────────────────────────────────────────────────────

def get_subtasks(task_id: int):
    return _query(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY sort_order, created_at", [task_id]
    )


def create_subtask(task_id: int, title: str):
    return _query(
        "INSERT INTO subtasks (task_id, title) VALUES (?, ?)", [task_id, title], fetch="lastrowid"
    )


def toggle_subtask(subtask_id: int):
    _query(
        "UPDATE subtasks SET is_done = CASE WHEN is_done = 1 THEN 0 ELSE 1 END WHERE id = ?",
        [subtask_id], fetch="none"
    )


def delete_subtask(subtask_id: int):
    _query("DELETE FROM subtasks WHERE id = ?", [subtask_id], fetch="none")


def update_subtask(subtask_id: int, title: str):
    _query("UPDATE subtasks SET title = ? WHERE id = ?", [title, subtask_id], fetch="none")


# ─── Time Log Operations ───────────────────────────────────────────────────────

def add_time_log(user_id: int, task_id: int, duration_minutes: float,
                 log_date: str = None, note: str = "", source: str = "manual",
                 subtask_id: int = None):
    if log_date is None:
        log_date = date.today().isoformat()
    return _query(
        """INSERT INTO time_logs (user_id, task_id, subtask_id, duration_minutes, log_date, note, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [user_id, task_id, subtask_id, duration_minutes, log_date, note, source],
        fetch="lastrowid"
    )


def get_time_logs(user_id: int, task_id: int = None, start_date: str = None,
                  end_date: str = None):
    query = """
        SELECT tl.*, t.title as task_title, c.name as category_name,
               c.color as category_color, c.icon as category_icon
        FROM time_logs tl
        JOIN tasks t ON tl.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE tl.user_id = ?
    """
    params = [user_id]
    if task_id:
        query += " AND tl.task_id = ?"
        params.append(task_id)
    if start_date:
        query += " AND tl.log_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND tl.log_date <= ?"
        params.append(end_date)
    query += " ORDER BY tl.log_date DESC, tl.created_at DESC"
    return _query(query, params)


def delete_time_log(log_id: int):
    _query("DELETE FROM time_logs WHERE id = ?", [log_id], fetch="none")


# ─── Analytics Queries ──────────────────────────────────────────────────────────

def get_daily_summary(user_id: int, target_date: str = None):
    if target_date is None:
        target_date = date.today().isoformat()
    return _query("""
        SELECT c.name as category_name, c.color, c.icon,
               t.title as task_title, t.id as task_id,
               SUM(tl.duration_minutes) as total_minutes
        FROM time_logs tl
        JOIN tasks t ON tl.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE tl.user_id = ? AND tl.log_date = ?
        GROUP BY c.id, t.id
        ORDER BY total_minutes DESC
    """, [user_id, target_date])


def get_weekly_summary(user_id: int, week_start: str = None):
    if week_start is None:
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
    week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()
    return _query("""
        SELECT c.name as category_name, c.color, c.icon,
               SUM(tl.duration_minutes) as total_minutes,
               COUNT(DISTINCT tl.log_date) as active_days
        FROM time_logs tl
        JOIN tasks t ON tl.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE tl.user_id = ? AND tl.log_date >= ? AND tl.log_date <= ?
        GROUP BY c.id
        ORDER BY total_minutes DESC
    """, [user_id, week_start, week_end])


def get_monthly_summary(user_id: int, year: int = None, month: int = None):
    if year is None:
        year = date.today().year
    if month is None:
        month = date.today().month
    month_start = f"{year}-{month:02d}-01"
    if month == 12:
        month_end = f"{year + 1}-01-01"
    else:
        month_end = f"{year}-{month + 1:02d}-01"
    return _query("""
        SELECT c.name as category_name, c.color, c.icon,
               SUM(tl.duration_minutes) as total_minutes,
               COUNT(DISTINCT tl.log_date) as active_days
        FROM time_logs tl
        JOIN tasks t ON tl.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE tl.user_id = ? AND tl.log_date >= ? AND tl.log_date < ?
        GROUP BY c.id
        ORDER BY total_minutes DESC
    """, [user_id, month_start, month_end])


def get_daily_trend(user_id: int, days: int = 30):
    start_date = (date.today() - timedelta(days=days)).isoformat()
    return _query("""
        SELECT tl.log_date, c.name as category_name, c.color,
               SUM(tl.duration_minutes) as total_minutes
        FROM time_logs tl
        JOIN tasks t ON tl.task_id = t.id
        JOIN categories c ON t.category_id = c.id
        WHERE tl.user_id = ? AND tl.log_date >= ?
        GROUP BY tl.log_date, c.id
        ORDER BY tl.log_date
    """, [user_id, start_date])


def get_task_total_time(task_id: int):
    result = _query(
        "SELECT COALESCE(SUM(duration_minutes), 0) as total FROM time_logs WHERE task_id = ?",
        [task_id], fetch="one"
    )
    if result:
        total = result['total']
        return float(total) if total else 0
    return 0
