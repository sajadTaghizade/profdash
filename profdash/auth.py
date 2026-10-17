"""Optional password protection for the dashboard.

`prof set-password` stores a salted scrypt hash in the database's config
table (never the password itself). When a hash is set, every dashboard
request needs HTTP Basic auth with that password (any username). The
PROFDASH_PASSWORD environment variable, if set, takes precedence.

Basic auth sends the password with every request, readable by anyone on
the network unless the connection is HTTPS. On localhost that's fine;
across a LAN or the internet, put profdash behind HTTPS (see
docs/self-hosting.md).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

CONFIG_KEY = "auth_password_hash"
ENV_VAR = "PROFDASH_PASSWORD"
_N, _R, _P = 2 ** 14, 8, 1
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        h = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                           n=int(n), r=int(r), p=int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(h.hex(), digest)


def read_hash(db_path: Path, *, strict: bool = False) -> str | None:
    """Stored hash, or None. With strict=True, database errors propagate
    instead of reading as "no password" (the request check must fail closed)."""
    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        try:
            row = conn.execute("SELECT value FROM config WHERE key = ?",
                               (CONFIG_KEY,)).fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        if strict:
            raise
        return None
    return row[0] if row and row[0] else None


def write_hash(db_path: Path, value: str | None) -> None:
    from .schema import create_all
    conn = sqlite3.connect(str(db_path), timeout=10)
    try:
        create_all(conn)
        if value is None:
            conn.execute("DELETE FROM config WHERE key = ?", (CONFIG_KEY,))
        else:
            conn.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                         (CONFIG_KEY, value))
        conn.commit()
    finally:
        conn.close()


def is_enabled(db_path: Path) -> bool:
    return bool(os.environ.get(ENV_VAR)) or read_hash(db_path) is not None


class Checker:
    """Verifies Basic auth headers; remembers headers that already passed so
    the (deliberately slow) scrypt check runs once per browser session."""

    def __init__(self, db_path_fn):
        self._db_path_fn = db_path_fn
        self._ok: set[str] = set()
        self._ok_for: str | None = None   # which secret the cache belongs to

    def _secret(self) -> tuple[str, str] | None:
        env = os.environ.get(ENV_VAR)
        if env:
            return ("env", env)
        try:
            path = self._db_path_fn()
        except (SystemExit, Exception):
            return None   # no database -> no stored hash (and nothing to protect)
        if not Path(path).exists():
            return None
        try:
            stored = read_hash(path, strict=True)
        except sqlite3.Error:
            return ("error", "")        # can't tell -> deny
        return ("hash", stored) if stored else None

    def required(self) -> bool:
        return self._secret() is not None

    def check(self, authorization: str | None) -> bool:
        secret = self._secret()
        if secret is None:
            return True
        if secret[0] == "error":
            return False
        if self._ok_for != secret[1]:          # password changed: drop cache
            self._ok, self._ok_for = set(), secret[1]
        if not authorization or not authorization.lower().startswith("basic "):
            return False
        if authorization in self._ok:
            return True
        try:
            decoded = base64.b64decode(authorization[6:].strip()).decode()
        except (ValueError, UnicodeDecodeError):
            return False
        password = decoded.split(":", 1)[1] if ":" in decoded else decoded
        kind, value = secret
        ok = (hmac.compare_digest(password.encode(), value.encode()) if kind == "env"
              else verify_password(password, value))
        if ok:
            self._ok.add(authorization)
        return ok
