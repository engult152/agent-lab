"""会话存储：本地 SQLite，或远程 Turso（设置 TURSO_URL 即切换）"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent
DB = _BASE / "data" / "chat.db"
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


def _retry(fn):
    """远端连接偶尔被掐断（ServerDisconnected），重建客户端重试一次"""
    global _client
    try:
        return fn()
    except Exception:
        _client = None
        return fn()


def _rows(sql, params=()):
    if TURSO_URL:
        return _retry(lambda: [tuple(r) for r in _remote().execute(sql, list(params)).rows])
    with sqlite3.connect(DB) as c:
        return c.execute(sql, params).fetchall()


def _run(sql, params=()):
    if TURSO_URL:
        _retry(lambda: _remote().execute(sql, list(params)))
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
        "id INTEGER PRIMARY KEY, title TEXT, created_at TEXT, owner TEXT)"
    )
    _run(
        "CREATE TABLE IF NOT EXISTS messages("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, "
        "role TEXT, content TEXT, created_at TEXT)"
    )
    _run("CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, n INTEGER)")
    _run(
        "CREATE TABLE IF NOT EXISTS files("
        "owner TEXT, name TEXT, content TEXT, is_binary INTEGER DEFAULT 0, "
        "updated_at TEXT, PRIMARY KEY(owner, name))"
    )
    try:
        _run("ALTER TABLE sessions ADD COLUMN owner TEXT")
    except Exception:
        pass
    try:
        _run("ALTER TABLE files ADD COLUMN is_binary INTEGER DEFAULT 0")
    except Exception:
        pass
    _ready = True


def new_session(title="新对话", owner=""):
    _init()
    sid = int(datetime.now().timestamp() * 1000)
    _run(
        "INSERT INTO sessions(id, title, created_at, owner) VALUES (?,?,?,?)",
        (sid, title, _now(), owner),
    )
    return sid


def last_session_id(owner=None):
    _init()
    if owner is None:
        rows = _rows("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
    else:
        rows = _rows(
            "SELECT id FROM sessions WHERE owner=? ORDER BY id DESC LIMIT 1", (owner,)
        )
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


def list_sessions(limit=10, owner=None):
    _init()
    if owner is None:
        return _rows(
            "SELECT id, title, created_at FROM sessions ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    return _rows(
        "SELECT id, title, created_at FROM sessions WHERE owner=? ORDER BY id DESC LIMIT ?",
        (owner, limit),
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

def save_file(owner, name, content, is_binary=False):
    _init()
    _run(
        "INSERT INTO files(owner, name, content, is_binary, updated_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(owner, name) DO UPDATE SET "
        "content=excluded.content, is_binary=excluded.is_binary, "
        "updated_at=excluded.updated_at",
        (owner, name, content, 1 if is_binary else 0, _now()),
    )


def list_files(owner):
    _init()
    return _rows("SELECT name, content, is_binary FROM files WHERE owner=?", (owner,))


def delete_file(owner, name):
    _init()
    _run("DELETE FROM files WHERE owner=? AND name=?", (owner, name))