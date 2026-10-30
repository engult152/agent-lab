"""极简 SQLite 持久化：会话 + 消息"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "chat.db"


def _conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute(
        "CREATE TABLE IF NOT EXISTS sessions("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, created_at TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS messages("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, "
        "role TEXT, content TEXT, created_at TEXT)"
    )
    return c


def new_session(title="新对话"):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO sessions(title, created_at) VALUES (?, ?)",
            (title, datetime.now().isoformat(timespec="seconds")),
        )
        return cur.lastrowid


def last_session_id():
    with _conn() as c:
        row = c.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None


def add_message(sid, role, content):
    with _conn() as c:
        c.execute(
            "INSERT INTO messages(session_id, role, content, created_at) VALUES (?,?,?,?)",
            (sid, role, content, datetime.now().isoformat(timespec="seconds")),
        )
        if role == "user":
            c.execute(
                "UPDATE sessions SET title=? WHERE id=? AND title='新对话'",
                (content[:20], sid),
            )


def load_messages(sid):
    with _conn() as c:
        return c.execute(
            "SELECT role, content FROM messages WHERE session_id=? ORDER BY id", (sid,)
        ).fetchall()
