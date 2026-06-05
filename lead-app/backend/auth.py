"""Authentifizierung: Passwort-Hashing (bcrypt) + JWT."""

import os
import time

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from database import get_session
from models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-bitte-in-produktion-aendern")
JWT_ALGO = "HS256"
TOKEN_TTL = 60 * 60 * 24 * 7  # 7 Tage

# auto_error=False → wir werfen selbst eine deutsche Fehlermeldung
oauth2 = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    # bcrypt: max 72 Bytes → vorher kürzen
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def get_current_user(
    token: str | None = Depends(oauth2),
    session: Session = Depends(get_session),
) -> User:
    if not token:
        raise HTTPException(401, "Nicht eingeloggt")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(401, "Token ungültig oder abgelaufen")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(401, "Benutzer nicht gefunden")
    return user
