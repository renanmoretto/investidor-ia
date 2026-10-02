"""All persistent data of the app, in one SQLite file. No other module reads or writes storage directly."""

import json
import logging
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent

DB_DIR = PROJECT_DIR / '.db'
# the Streamlit version of the app kept its data here
LEGACY_DB_DIR = PROJECT_DIR / 'db'

DB_FILE_NAME = 'investidor_ia.db'
# earlier versions kept only the chat agent data in SQLite, in this file
LEGACY_DB_FILE_NAME = 'agents_db.db'

# earlier versions kept these as JSON files in the db dir
LEGACY_MODEL_FILE_NAME = 'model.json'
LEGACY_API_KEYS_FILE_NAME = 'api_keys.json'
LEGACY_REPORTS_FILE_NAME = 'reports.json'
MIGRATED_SUFFIX = '.migrated'

BUSY_TIMEOUT_SECONDS = 10

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_keys (
    provider TEXT PRIMARY KEY,
    api_key TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    investor_name TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_sessions (
    id TEXT PRIMARY KEY,
    last_investor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chats (
    session_id TEXT NOT NULL,
    investor TEXT NOT NULL,
    agent_session_id TEXT NOT NULL,
    PRIMARY KEY (session_id, investor)
);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_session_id TEXT NOT NULL,
    message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS chat_messages_agent_session_id ON chat_messages (agent_session_id);
"""

_initialized = False


def db_file() -> Path:
    return DB_DIR / DB_FILE_NAME


def init() -> None:
    """Creates the db dir, the file and the tables, and brings in the data of earlier versions.
    It runs one time, on the first use of the database."""
    global _initialized
    if _initialized:
        return
    _ensure_db_dir()
    _rename_legacy_db_file()
    with _connection() as conn:
        # WAL lets the chat agent (its own async connection to this file) and the app write without blocking readers
        conn.execute('PRAGMA journal_mode=WAL')
        conn.executescript(SCHEMA)
        removed = conn.execute('DELETE FROM cache WHERE expires_at < ?', (time.time(),)).rowcount
    logger.info('db ready at %s expired_cache_rows_removed=%d', db_file(), removed)
    _initialized = True
    _migrate_json_files()


def _ensure_db_dir() -> None:
    if DB_DIR.exists():
        return
    if LEGACY_DB_DIR.exists():
        LEGACY_DB_DIR.rename(DB_DIR)
        logger.info('db dir migrated from %s to %s', LEGACY_DB_DIR, DB_DIR)
        return
    DB_DIR.mkdir(parents=True)
    logger.info('db dir created at %s', DB_DIR)


def _rename_legacy_db_file() -> None:
    legacy = DB_DIR / LEGACY_DB_FILE_NAME
    if db_file().exists() or not legacy.exists():
        return
    # the -wal and -shm files hold data that is not in the main file yet, so they must move with it
    for suffix in ('', '-wal', '-shm'):
        source = legacy.with_name(legacy.name + suffix)
        if source.exists():
            source.rename(db_file().with_name(db_file().name + suffix))
    logger.info('db file renamed from %s to %s', legacy.name, db_file().name)


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_file(), timeout=BUSY_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    init()
    with _connection() as conn:
        yield conn


# settings


def get_setting(key: str) -> str | None:
    with _connect() as conn:
        row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    return row['value'] if row else None


def set_setting(key: str, value: str) -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value',
            (key, value),
        )


def get_api_keys() -> dict[str, str]:
    with _connect() as conn:
        rows = conn.execute('SELECT provider, api_key FROM api_keys').fetchall()
    return {row['provider']: row['api_key'] for row in rows}


def set_api_key(provider: str, api_key: str) -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO api_keys (provider, api_key) VALUES (?, ?) '
            'ON CONFLICT (provider) DO UPDATE SET api_key = excluded.api_key',
            (provider, api_key),
        )


# reports


def _report_from_row(row: sqlite3.Row) -> dict:
    return {**dict(row), 'data': json.loads(row['data'])}


def list_reports() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute('SELECT * FROM reports ORDER BY generated_at DESC').fetchall()
    return [_report_from_row(row) for row in rows]


def get_report(report_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
    return _report_from_row(row) if row else None


def insert_report(report: dict) -> None:
    with _connect() as conn:
        _insert_report(conn, report)


def _insert_report(conn: sqlite3.Connection, report: dict) -> None:
    conn.execute(
        'INSERT INTO reports (id, ticker, investor_name, generated_at, data) VALUES (?, ?, ?, ?, ?)',
        (
            report['id'],
            report['ticker'],
            report['investor_name'],
            report['generated_at'],
            json.dumps(report['data'], ensure_ascii=False),
        ),
    )


def delete_report(report_id: str) -> bool:
    with _connect() as conn:
        return conn.execute('DELETE FROM reports WHERE id = ?', (report_id,)).rowcount > 0


# cache


def cache_get(key: str):
    """Returns None when the key is not in the cache or is expired."""
    with _connect() as conn:
        row = conn.execute('SELECT value FROM cache WHERE key = ? AND expires_at > ?', (key, time.time())).fetchone()
    return json.loads(row['value']) if row else None


def cache_set(key: str, value, expire: int) -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO cache (key, value, expires_at) VALUES (?, ?, ?) '
            'ON CONFLICT (key) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at',
            (key, json.dumps(value, ensure_ascii=False), time.time() + expire),
        )


# chat


def get_chat_session(session_id: str) -> dict | None:
    """The session with its chats and their messages, in the order they were sent."""
    with _connect() as conn:
        session = conn.execute('SELECT * FROM chat_sessions WHERE id = ?', (session_id,)).fetchone()
        if not session:
            return None
        chats = conn.execute('SELECT * FROM chats WHERE session_id = ?', (session_id,)).fetchall()
        messages = {
            chat['agent_session_id']: conn.execute(
                'SELECT message FROM chat_messages WHERE agent_session_id = ? ORDER BY id',
                (chat['agent_session_id'],),
            ).fetchall()
            for chat in chats
        }
    return {
        'id': session['id'],
        'last_investor': session['last_investor'],
        'chats': [
            {
                'investor': chat['investor'],
                'agent_session_id': chat['agent_session_id'],
                'messages': [json.loads(row['message']) for row in messages[chat['agent_session_id']]],
            }
            for chat in chats
        ],
    }


def save_chat_session(session_id: str, last_investor: str) -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO chat_sessions (id, last_investor) VALUES (?, ?) '
            'ON CONFLICT (id) DO UPDATE SET last_investor = excluded.last_investor',
            (session_id, last_investor),
        )


def save_chat(session_id: str, investor: str, agent_session_id: str) -> None:
    """Sets the conversation of the investor in the session. The messages of the conversation it replaces are deleted."""
    with _connect() as conn:
        old = conn.execute(
            'SELECT agent_session_id FROM chats WHERE session_id = ? AND investor = ?', (session_id, investor)
        ).fetchone()
        if old and old['agent_session_id'] != agent_session_id:
            conn.execute('DELETE FROM chat_messages WHERE agent_session_id = ?', (old['agent_session_id'],))
        conn.execute(
            'INSERT INTO chats (session_id, investor, agent_session_id) VALUES (?, ?, ?) '
            'ON CONFLICT (session_id, investor) DO UPDATE SET agent_session_id = excluded.agent_session_id',
            (session_id, investor, agent_session_id),
        )


def add_chat_message(agent_session_id: str, message: dict) -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO chat_messages (agent_session_id, message) VALUES (?, ?)',
            (agent_session_id, json.dumps(message, ensure_ascii=False)),
        )


# data of earlier versions


def _read_legacy_json(path: Path):
    content = path.read_text().strip()
    return json.loads(content) if content else None


def _migrate_json_files() -> None:
    """Copies the JSON files of earlier versions into the tables. A file is renamed after its data is saved,
    so it is read one time only. A file with invalid JSON is not renamed and not read."""
    for name, migrate in (
        (LEGACY_MODEL_FILE_NAME, _migrate_model),
        (LEGACY_API_KEYS_FILE_NAME, _migrate_api_keys),
        (LEGACY_REPORTS_FILE_NAME, _migrate_reports),
    ):
        path = DB_DIR / name
        if not path.exists():
            continue
        try:
            content = _read_legacy_json(path)
            with _connection() as conn:
                count = migrate(conn, content) if content else 0
        except (json.JSONDecodeError, TypeError, KeyError, AttributeError, sqlite3.Error):
            logger.exception('legacy file %s not migrated, it stays in place', name)
            continue
        path.rename(path.with_name(name + MIGRATED_SUFFIX))
        logger.info('legacy file %s migrated rows=%d, renamed to %s', name, count, name + MIGRATED_SUFFIX)


def _migrate_model(conn: sqlite3.Connection, content: dict) -> int:
    rows = [(key, content[key]) for key in ('provider', 'model') if content.get(key)]
    conn.executemany('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', rows)
    return len(rows)


def _migrate_api_keys(conn: sqlite3.Connection, content: dict) -> int:
    rows = [(provider, api_key) for provider, api_key in content.items() if api_key]
    conn.executemany('INSERT OR IGNORE INTO api_keys (provider, api_key) VALUES (?, ?)', rows)
    return len(rows)


def _migrate_reports(conn: sqlite3.Connection, content: list[dict]) -> int:
    for report in content:
        # reports from the Streamlit version have no id
        _insert_report(conn, {**report, 'id': report.get('id') or uuid.uuid4().hex})
    return len(content)
