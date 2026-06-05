"""SQLite-Datenbank (SQLModel) — Engine, Session, Initialisierung."""

import os

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./leadfinder.db")

# Railway/Heroku liefern teils das alte "postgres://"-Schema – SQLAlchemy braucht "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    """Legt die Tabellen an (idempotent)."""
    import models  # noqa: F401  – Modelle registrieren, bevor create_all läuft

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
