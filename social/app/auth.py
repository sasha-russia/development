"""Logins and signed session cookies."""

import base64
import hashlib
import hmac
import os

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from . import config
from .db import SessionLocal, User

COOKIE = "social_session"
MAX_AGE = 14 * 24 * 3600
_signer = URLSafeTimedSerializer(config.SECRET_KEY, salt="session")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(actual, base64.b64decode(digest))


def ensure_admin(db) -> None:
    if db.scalar(select(User.id).limit(1)) or not config.ADMIN_PASSWORD:
        return
    db.add(User(login=config.ADMIN_LOGIN, password_hash=hash_password(config.ADMIN_PASSWORD), is_admin=True))
    db.commit()


def make_cookie(user: User) -> str:
    return _signer.dumps({"uid": user.id})


def current_user(request: Request) -> User | None:
    raw = request.cookies.get(COOKIE)
    if not raw:
        return None
    try:
        data = _signer.loads(raw, max_age=MAX_AGE)
    except BadSignature:
        return None
    with SessionLocal() as db:
        return db.get(User, data.get("uid"))


def require_user(request: Request) -> User:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    # Cookie is SameSite=Lax; also refuse cross-site state changes outright.
    if request.method not in ("GET", "HEAD"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != str(request.base_url).rstrip("/") and origin != config.BASE_URL:
            raise HTTPException(status_code=403, detail="Bad origin")
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if not user.is_admin:
        raise HTTPException(status_code=403)
    return user
