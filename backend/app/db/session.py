"""Database engine and per-request session dependency."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(
    get_settings().database_url.get_secret_value(),
    # Checks the connection before using it; the pooler may close idle ones.
    pool_pre_ping=True,
    # Keeps statement values (password hashes, salaries) out of error messages
    # and therefore out of the logs.
    hide_parameters=True,
    # psycopg 3 turns a query run 5 times on one connection into a server-side
    # prepared statement (_pg3_0, _pg3_1...). Behind Supabase's pooler a server
    # connection can be handed to another client that names its statements the
    # same way, and the query fails with DuplicatePreparedStatement. None turns
    # server-side preparing off; the cost is negligible at this size.
    connect_args={"prepare_threshold": None},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    with SessionLocal() as session:
        yield session
