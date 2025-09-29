import os
from contextlib import contextmanager
from typing import Generator, Iterator, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from fair_platform.backend.data.storage import storage

from dotenv import load_dotenv

load_dotenv()

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_session",
    "init_db",
    "get_database_url",
    "session_dependency",
]


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("Using SQLite since DATABASE_URL is not set")
        return f"sqlite:///{storage.local_db_path}"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


DATABASE_URL = get_database_url()

_engine_kwargs: dict[str, Any] = dict(future=True, pool_pre_ping=True)

if DATABASE_URL.startswith("sqlite:"):
    # Allow usage across threads (useful for dev servers)
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)

Base = declarative_base()


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Context manager for a DB session.
    Usage:
        with get_session() as session:
            session.query(...)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def session_dependency() -> Generator:
    with get_session() as session:
        yield session


def init_db(create_all: bool = True) -> None:
    """
    Initialize database artifacts.
    By default, calls Base.metadata.create_all; safe to call multiple times.
    """
    if create_all:
        from . import models  # noqa: F401

        Base.metadata.create_all(bind=engine)


# Optional eager initialization in simple scripts (disabled by default)
if os.getenv("FAIR_AUTO_INIT_DB") == "1":
    init_db()
