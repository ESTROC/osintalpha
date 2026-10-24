"""SQLite persistence, short-lived connections, explicit constraints and audit history."""
import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path():
    return Path(os.getenv('OSINTALPHA_DB_PATH', './instance/osintalpha.db')).resolve()


@contextmanager
def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(p), timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connect() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          passhash TEXT NOT NULL, salt TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin'
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS cases (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, subject_type TEXT NOT NULL,
          query TEXT NOT NULL, purpose TEXT NOT NULL,
          authority_confirmed INTEGER NOT NULL,
          ai_opt_in INTEGER NOT NULL DEFAULT 0,
          created_by TEXT NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
          last_collected TEXT
        );
        CREATE TABLE IF NOT EXISTS evidence (
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          provider TEXT NOT NULL, label TEXT NOT NULL, summary TEXT NOT NULL,
          source_url TEXT NOT NULL, source_ref TEXT NOT NULL DEFAULT '',
          fetched_at TEXT NOT NULL, observed_at TEXT,
          sha256 TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'candidate',
          reviewer_notes TEXT NOT NULL DEFAULT '', reviewed_by TEXT,
          reviewed_at TEXT,
          raw_json TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_evidence ON evidence(case_id,provider,source_ref);
        CREATE INDEX IF NOT EXISTS evidence_case_idx ON evidence(case_id);
        CREATE TABLE IF NOT EXISTS collection_runs (
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
          provider TEXT NOT NULL, state TEXT NOT NULL, result_count INTEGER NOT NULL,
          message TEXT NOT NULL, ran_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
          id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
          object_type TEXT NOT NULL, object_id TEXT NOT NULL, details TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        ''')
        password = os.environ.get('OSINTALPHA_ADMIN_PASSWORD')
        if not password or len(password) < 12:
            raise RuntimeError('Set OSINTALPHA_ADMIN_PASSWORD to a unique password of at least 12 characters in the environment.')
        existing = c.execute('SELECT id FROM users WHERE username=?', ('admin',)).fetchone()
        if not existing:
            salt = secrets.token_hex(16)
            digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
            c.execute('INSERT INTO users(id, username, passhash, salt) VALUES (?,?,?,?)',
                      (secrets.token_hex(16), 'admin', digest, salt))


def verify_password(password, row):
    expected = bytes.fromhex(row['passhash'])
    actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(row['salt']), n=16384, r=8, p=1)
    return secrets.compare_digest(actual, expected)


def audit(actor, action, object_type, object_id, details=''):
    with connect() as c:
        c.execute('INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)',
                  (secrets.token_hex(12), actor, action, object_type, object_id, details[:500], utcnow()))
