"""Database setup and session helpers."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base, User
from services.auth_service import hash_password
from utils.constants import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, ROLE_ADMIN

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'turkak_app.db'}")
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a database session and commit/rollback safely."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Create tables and seed the default admin user when the user table is empty."""
    Base.metadata.create_all(bind=engine)
    with get_session() as db:
        existing = db.query(User).first()
        if existing:
            return
        db.add(
            User(
                username=DEFAULT_ADMIN_USERNAME,
                full_name="Admin",
                email=DEFAULT_ADMIN_EMAIL,
                role=ROLE_ADMIN,
                active=True,
                must_change_password=True,
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            )
        )
