"""Optional username/password identities for the Web application.

Business-data access remains gated for ordinary users until tenant isolation is
complete. This module never copies or rewrites legacy records on registration.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src import auth
from src.storage import DatabaseManager, WebUser

COOKIE_NAME = "dsa_user_session"
_USERNAME = re.compile(r"^[a-zA-Z0-9_]{3,32}$")
_HASH_ITERATIONS = 600_000


@dataclass(frozen=True)
class Identity:
    id: str
    username: str
    role: str


def enabled() -> bool:
    """Read the explicit opt-in on each request, matching legacy auth semantics."""
    auth._ensure_env_loaded()
    env_file = os.getenv("ENV_FILE")
    path = Path(env_file) if env_file else Path(__file__).resolve().parent.parent / ".env"
    if not path.exists():
        return False
    return (dotenv_values(path).get("WEB_ACCOUNTS_ENABLED") or "").strip().lower() == "true"


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _HASH_ITERATIONS)
    return f"pbkdf2_sha256${_HASH_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(rounds)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def _validate(username: str, password: str) -> None:
    if not _USERNAME.fullmatch(username):
        raise ValueError("用户名需为 3–32 位英文字母、数字或下划线")
    if len(password) < 8 or len(password) > 256:
        raise ValueError("密码需为 8–256 位")


def has_admin() -> bool:
    with DatabaseManager.get_instance().session_scope() as session:
        return session.get(WebUser, "admin") is not None


def register(username: str, password: str, *, first_admin: bool = False) -> Identity:
    username = username.strip().lower()
    _validate(username, password)
    user = WebUser(
        id="admin" if first_admin else uuid.uuid4().hex,
        username=username,
        password_hash=_hash_password(password),
        role="admin" if first_admin else "user",
        session_version=1,
    )
    try:
        with DatabaseManager.get_instance().session_scope() as session:
            if not first_admin and session.get(WebUser, "admin") is None:
                raise ValueError("请先在服务器本机创建管理员账号")
            session.add(user)
            session.flush()
            identity = Identity(user.id, user.username, user.role)
    except IntegrityError as exc:
        raise ValueError("用户名已存在，或管理员已创建") from exc
    return identity


def authenticate(username: str, password: str) -> Identity | None:
    with DatabaseManager.get_instance().session_scope() as session:
        user = session.scalar(select(WebUser).where(WebUser.username == username.strip().lower()))
        if user is None or not _verify_password(password, user.password_hash):
            return None
        return Identity(user.id, user.username, user.role)


def create_session(identity: Identity) -> str:
    secret = auth._load_session_secret()
    if not secret:
        raise RuntimeError("无法创建会话密钥")
    with DatabaseManager.get_instance().session_scope() as session:
        user = session.get(WebUser, identity.id)
        if user is None:
            raise ValueError("账号不存在")
        version = user.session_version
    payload = f"{identity.id}.{version}.{int(time.time())}.{secrets.token_hex(16)}"
    signature = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session(value: str | None) -> Identity | None:
    if not value:
        return None
    parts = value.split(".")
    if len(parts) != 5:
        return None
    user_id, version_raw, timestamp_raw, _nonce, signature = parts
    payload = ".".join(parts[:-1])
    secret = auth._load_session_secret()
    if not secret or not hmac.compare_digest(
        hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest(), signature
    ):
        return None
    try:
        version = int(version_raw)
        timestamp = int(timestamp_raw)
        max_hours = int(os.getenv("ADMIN_SESSION_MAX_AGE_HOURS", "24"))
    except ValueError:
        return None
    age = time.time() - timestamp
    if age < 0 or age > max_hours * 3600:
        return None
    with DatabaseManager.get_instance().session_scope() as session:
        user = session.get(WebUser, user_id)
        if user is None or user.session_version != version:
            return None
        return Identity(user.id, user.username, user.role)


def revoke_sessions(user_id: str) -> None:
    with DatabaseManager.get_instance().session_scope() as session:
        user = session.get(WebUser, user_id)
        if user is not None:
            user.session_version += 1
