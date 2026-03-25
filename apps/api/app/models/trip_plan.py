from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TripPlanRecord(Base):
    __tablename__ = "trip_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    planning_session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="assistant")

    raw_brief: Mapped[str] = mapped_column(Text, nullable=False)

    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pace_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget: Mapped[str | None] = mapped_column(String(50), nullable=True)

    missing_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")

    candidate_places: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    itinerary_skeleton: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)

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