"""SQLAlchemy engine and session management.

Supports both SQLite (dev) and PostgreSQL/Supabase (production).
Used alongside legacy db.py — phased migration.

Env vars:
  DATABASE_URL       — PostgreSQL/Supabase connection string
                       (default: sqlite:///cbse_content.db)
  SUPABASE_URL       — Supabase project URL (alternative to DATABASE_URL)
  SUPABASE_SERVICE_KEY — Supabase service_role key
  DB_POOL_SIZE       — connection pool size (default: 5)
  DB_ECHO            — log all SQL (default: false)
"""

import os
import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session as SASession, sessionmaker

from models import Base, ALL_MODELS

log = logging.getLogger("cbse.db_sa")

_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine
    database_url = os.environ.get("DATABASE_URL", "")
    echo = os.environ.get("DB_ECHO", "").lower() in ("1", "true", "yes")

    if database_url:
        url = database_url
    else:
        url = "sqlite:///cbse_content.db"

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        url,
        echo=echo,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
        max_overflow=10,
        connect_args=connect_args,
    )

    if url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    log.info("SQLAlchemy engine created: %s (%s)", url.split("@")[0] if "@" in url else url, "echo" if echo else "silent")
    return _engine


def get_session() -> SASession:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()


def init_tables():
    """Create all tables if they don't exist. Safe to call repeatedly."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    log.info("Database tables verified (%d models)", len(ALL_MODELS))


def close_session(session: SASession):
    """Safely close a session."""
    try:
        session.close()
    except Exception as e:
        log.warning("Error closing session: %s", e)


def get_db_status() -> dict:
    """Return database connectivity status."""
    try:
        session = get_session()
        result = session.execute(text("SELECT COUNT(*) FROM boards")).scalar()
        session.close()
        return {
            "connected": True,
            "backend": "postgresql" if "postgres" in str(get_engine().url) else "sqlite",
            "boards": result,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
        }
