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
    if engine.dialect.name != "postgresql":
        return

    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def _ensure_trip_plan_step2_columns() -> None:
    inspector = inspect(engine)

    if "trip_plans" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("trip_plans")}
    statements: list[str] = []

    if engine.dialect.name == "postgresql":
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
    else:
        if "candidate_places" not in existing_columns:
            statements.append(
                "ALTER TABLE trip_plans "
                "ADD COLUMN candidate_places JSON NOT NULL DEFAULT '[]'"
            )

        if "itinerary_skeleton" not in existing_columns:
            statements.append(
                "ALTER TABLE trip_plans "
                "ADD COLUMN itinerary_skeleton JSON NOT NULL DEFAULT '[]'"
            )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _ensure_review_intelligence_step2_columns() -> None:
    inspector = inspect(engine)

    if "review_intelligence" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("review_intelligence")}
    statements: list[str] = []
    post_statements: list[str] = []

    if "review_signature" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN review_signature VARCHAR(64) NOT NULL DEFAULT ''"
        )

    if "created_at" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "updated_at" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "refreshed_at" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN refreshed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "review_signature" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET review_signature = COALESCE(review_signature, '')"
        )

    if "refreshed_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET refreshed_at = COALESCE(refreshed_at, CURRENT_TIMESTAMP)"
        )

    if "updated_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)"
        )

    if "created_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
        )

    if not statements and not post_statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        for statement in post_statements:
            connection.execute(text(statement))


def create_db_tables() -> None:
    enable_pgvector_extension()
    Base.metadata.create_all(bind=engine)
    _ensure_trip_plan_step2_columns()
    _ensure_review_intelligence_step2_columns()


def get_db_session() -> Session:
    return SessionLocal()