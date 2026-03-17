import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

load_dotenv()

_engine = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    database_url = os.getenv("DATABASE_URL", "sqlite:///data/outreach.db")

    # For SQLite, ensure the data directory exists before creating the engine
    if database_url.startswith("sqlite:///"):
        db_path_str = database_url[len("sqlite:///"):]
        db_path = Path(db_path_str)
        # Resolve relative paths from the project root (parent of this file's directory)
        if not db_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            db_path = project_root / db_path_str
            database_url = f"sqlite:///{db_path}"
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
    )

    # Apply SQLite-specific pragmas on every new connection
    if database_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return _engine


def get_session() -> Session:
    """Return a new SQLAlchemy Session bound to the shared engine.

    Callers are responsible for committing/rolling back and closing:

        session = get_session()
        try:
            ...
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    Or use it as a context manager (SQLAlchemy 2.x Session supports that):

        with get_session() as session:
            ...
    """
    engine = get_engine()
    return Session(bind=engine)


def init_db():
    """Create all tables defined in models.py if they do not already exist."""
    from database.models import Base  # local import avoids circular deps at module load
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
