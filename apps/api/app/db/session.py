from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import get_settings

settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False