"""
MTCB Authentication Database and Security Service.
Uses Python standard library (sqlite3, hashlib, secrets) for zero-dependency,
cryptographically secure user authentication.
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# Database path in backend/data/mtcb.db
DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "mtcb.db"

# Security parameters
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16
TOKEN_BYTES = 32
SESSION_EXPIRY_DAYS = 7


def get_db_connection() -> sqlite3.Connection:
    """Create a thread-safe connection to SQLite with row-factory and WAL mode."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize database tables for users and sessions."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    finally:
        conn.close()


def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256 with 100k rounds and a cryptographic salt.
    Returns (password_hash_hex, salt_hex).
    """
    if salt_hex is None:
        salt = secrets.token_bytes(SALT_BYTES)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS
    )
    return derived.hex(), salt_hex


def verify_password(password: str, password_hash: str, salt_hex: str) -> bool:
    """Verify password in constant time to prevent timing attacks."""
    computed_hash, _ = hash_password(password, salt_hex)
    return secrets.compare_digest(computed_hash, password_hash)


def register_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user and create an initial session token."""
    name = name.strip()
    email = email.strip().lower()

    if not name or len(name) < 2:
        raise ValueError("Name must be at least 2 characters long.")
    if not email or "@" not in email or "." not in email:
        raise ValueError("Please provide a valid email address.")
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    pw_hash, salt_hex = hash_password(password)
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash, salt, created_at, last_login_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (name, email, pw_hash, salt_hex, now_iso, now_iso)
            )
            user_id = cursor.lastrowid

            token = secrets.token_urlsafe(TOKEN_BYTES)
            expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

            cursor.execute(
                """
                INSERT INTO sessions (token, user_id, created_at, expires_at)
                VALUES (?, ?, ?, ?);
                """,
                (token, user_id, now_iso, expires_at)
            )

            return {
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "created_at": now_iso
                },
                "token": token
            }
    except sqlite3.IntegrityError:
        raise ValueError(f"An account with email '{email}' already exists.")
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate a user by email and password, creating a new session token."""
    email = email.strip().lower()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, password_hash, salt, created_at FROM users WHERE email = ?;",
            (email,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Invalid email or password.")

        if not verify_password(password, row["password_hash"], row["salt"]):
            raise ValueError("Invalid email or password.")

        now_iso = datetime.now(timezone.utc).isoformat()
        token = secrets.token_urlsafe(TOKEN_BYTES)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

        with conn:
            conn.execute(
                "UPDATE users SET last_login_at = ? WHERE id = ?;",
                (now_iso, row["id"])
            )
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?);",
                (token, row["id"], now_iso, expires_at)
            )

        return {
            "user": {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "created_at": row["created_at"]
            },
            "token": token
        }
    finally:
        conn.close()


def get_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve user details for a valid, non-expired session token."""
    if not token:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            SELECT u.id, u.name, u.email, u.created_at, u.last_login_at, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?;
            """,
            (token, now_iso)
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "created_at": row["created_at"],
            "last_login_at": row["last_login_at"]
        }
    finally:
        conn.close()


def invalidate_session(token: str) -> bool:
    """Invalidate a session on logout."""
    if not token:
        return False
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE token = ?;", (token,))
            return cursor.rowcount > 0
    finally:
        conn.close()
