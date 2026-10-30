"""会话存储：本地 SQLite，或远程 Turso（设置 TURSO_URL 即切换）"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path(__file__).resolve().parent / "data" / "chat.db"
TURSO_URL = os.environ.get("TURSO_URL", "").strip()
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "").strip()

_client = None
_ready = False


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _remote():
    global _client
    if _client is None:
        import libsql_client

        url = TURSO_URL.replace("libsql://", "https://")
        _client = libsql_client.create_client_sync(url, auth_token=TURSO_TOKEN)
    return _client


def _rows(sql, params=()):
    if TURSO_URL:
        return [tuple(r) for r in _remote().execute(sql, list(params)).rows]
    with sqlite3.connect(DB) as c:
        return c.execute(sql, params).fetchall()


def _run(sql, params=()):
    if TURSO_URL:
        _remote().execute(sql, list(params))
        return
    with sqlite3.connect(DB) as c:
        c.execute(sql, params)


def _init():
    global _ready
    if _ready:
        return
    DB.parent.mkdir(parents=True, exist_ok=True)
    _run(
        "CREATE TABLE IF NOT EXISTS sessions("
        "id INTEGER PRIMARY KEY, title TEXT, created_at TEXT)"
    )
    _run(
        "CREATE TABLE IF NOT EXISTS messages("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, "
        "role TEXT, content TEXT, created_at TEXT)"
    )
    _run("CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, n INTEGER)")
    _ready = True


def new_session(title="新对话"):
    _init()
    sid = int(datetime.now().timestamp() * 1000)
    _run(
        "INSERT INTO sessions(id, title, created_at) VALUES (?,?,?)",
        (sid, title, _now()),
    )
    return sid


def last_session_id():
    _init()
    rows = _rows("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
    return rows[0][0] if rows else None


def add_message(sid, role, content):
    _init()
    _run(
        "INSERT INTO messages(session_id, role, content, created_at) VALUES (?,?,?,?)",
        (sid, role, content, _now()),
    )
    if role == "user":
        _run(
            "UPDATE sessions SET title=? WHERE id=? AND title='新对话'",
            (content[:20], sid),
        )


def load_messages(sid):
    _init()
    return _rows(
        "SELECT role, content FROM messages WHERE session_id=? ORDER BY id", (sid,)
    )


def list_sessions(limit=10):
    _init()
    return _rows(
        "SELECT id, title, created_at FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
    )


def usage_today():
    _init()
    today = datetime.now().date().isoformat()
    rows = _rows("SELECT n FROM usage WHERE day=?", (today,))
    return rows[0][0] if rows else 0


def bump_usage():
    _init()
    today = datetime.now().date().isoformat()
    _run(
        "INSERT INTO usage(day, n) VALUES (?, 1) "
        "ON CONFLICT(day) DO UPDATE SET n = n + 1",
        (today,),
    )