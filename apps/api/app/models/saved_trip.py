from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SavedTripRecord(Base):
    __tablename__ = "saved_trips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="assistant")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planning")

    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    companions: Mapped[str | None] = mapped_column(String(50), nullable=True)

    current_parsed_constraints: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    current_candidate_places: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    current_itinerary: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    current_itinerary_skeleton: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    comparison_context: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_version_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    history_branch_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    selected_places_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_recommendations_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replaced_slots_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ItineraryVersionRecord(Base):
    __tablename__ = "itinerary_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="assistant")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planning")

    is_current: Mapped[bool] = mapped_column(nullable=False, default=False)
    branch_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parent_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    restored_from_version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parsed_constraints: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    candidate_places: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    itinerary: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    itinerary_skeleton: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    comparison_context: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class TripSignalRecord(Base):
    __tablename__ = "trip_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slot_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )