from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models import (
    ItineraryVersionRecord,
    ReviewIntelligenceRecord,
    SavedTripRecord,
    TravellerMemoryRecord,
    TravellerPersonaEmbeddingRecord,
    TravellerPersonaRecord,
    TripPlanRecord,
    TripSignalRecord,
)  # noqa: F401

settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
)


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def enable_pgvector_extension() -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _ensure_trip_plan_step2_columns() -> None:
    inspector = inspect(engine)

    if "trip_plans" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("trip_plans")}

    statements: list[str] = []

    if "candidate_places" not in existing_columns:
        statements.append(
            "ALTER TABLE trip_plans "
            "ADD COLUMN candidate_places JSON NOT NULL DEFAULT '[]'::json"
        )

    if "itinerary_skeleton" not in existing_columns:
        statements.append(
            "ALTER TABLE trip_plans "
            "ADD COLUMN itinerary_skeleton JSON NOT NULL DEFAULT '[]'::json"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def create_db_tables() -> None:
    enable_pgvector_extension()
    Base.metadata.create_all(bind=engine)
    _ensure_trip_plan_step2_columns()


def get_db_session() -> Session:
    return SessionLocal()