"""Datenbank-Modelle (SQLModel) + Request/Response-Schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


def _uid() -> str:
    return uuid.uuid4().hex


# ── Tabellen ────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    id: str = Field(default_factory=_uid, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SavedSearch(SQLModel, table=True):
    id: str = Field(default_factory=_uid, primary_key=True)
    user_id: str = Field(index=True, foreign_key="user.id")
    label: str
    stadt: str
    level: str = "8"
    kategorien: str | None = None  # JSON-String einer Liste oder None
    nur_mit_telefon: bool = True
    count: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Schemas (API) ───────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    email: str


class SavedSearchIn(BaseModel):
    label: str
    stadt: str
    level: str = "8"
    kategorien: list[str] | None = None
    nur_mit_telefon: bool = True
    count: int | None = None


class SavedSearchOut(BaseModel):
    id: str
    label: str
    stadt: str
    level: str
    kategorien: list[str] | None = None
    nur_mit_telefon: bool
    count: int | None = None
