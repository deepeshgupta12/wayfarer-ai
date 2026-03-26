from __future__ import annotations

from threading import Lock

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models import (
    ItineraryVersionRecord,
    LocationRelationRecord,
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

_SCHEMA_INIT_LOCK = Lock()
_SCHEMA_INITIALIZED = False


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
            "ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "updated_at" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "refreshed_at" not in existing_columns:
        statements.append(
            "ALTER TABLE review_intelligence "
            "ADD COLUMN refreshed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        )

    if "review_signature" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET review_signature = '' "
            "WHERE review_signature IS NULL"
        )

    if "created_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET created_at = CURRENT_TIMESTAMP "
            "WHERE created_at IS NULL"
        )

    if "updated_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET updated_at = CURRENT_TIMESTAMP "
            "WHERE updated_at IS NULL"
        )

    if "refreshed_at" not in existing_columns:
        post_statements.append(
            "UPDATE review_intelligence "
            "SET refreshed_at = CURRENT_TIMESTAMP "
            "WHERE refreshed_at IS NULL"
        )

    if not statements and not post_statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        for statement in post_statements:
            connection.execute(text(statement))

def _ensure_step5_comparison_context_columns() -> None:
    inspector = inspect(engine)
    statements: list[str] = []

    json_default = "'{}'::json" if engine.dialect.name == "postgresql" else "'{}'"

    if "trip_plans" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("trip_plans")}
        if "comparison_context" not in existing_columns:
            statements.append(
                "ALTER TABLE trip_plans "
                f"ADD COLUMN comparison_context JSON NOT NULL DEFAULT {json_default}"
            )

    if "saved_trips" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("saved_trips")}
        if "comparison_context" not in existing_columns:
            statements.append(
                "ALTER TABLE saved_trips "
                f"ADD COLUMN comparison_context JSON NOT NULL DEFAULT {json_default}"
            )

    if "itinerary_versions" in inspector.get_table_names():
        existing_columns = {column["name"] for column in inspector.get_columns("itinerary_versions")}
        if "comparison_context" not in existing_columns:
            statements.append(
                "ALTER TABLE itinerary_versions "
                f"ADD COLUMN comparison_context JSON NOT NULL DEFAULT {json_default}"
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
    _ensure_review_intelligence_step2_columns()
    _ensure_step5_comparison_context_columns()


def ensure_runtime_schema_ready() -> None:
    global _SCHEMA_INITIALIZED

    if _SCHEMA_INITIALIZED:
        return

    with _SCHEMA_INIT_LOCK:
        if _SCHEMA_INITIALIZED:
            return
        create_db_tables()
        _SCHEMA_INITIALIZED = True


def get_db_session() -> Session:
    ensure_runtime_schema_ready()
    return SessionLocal()