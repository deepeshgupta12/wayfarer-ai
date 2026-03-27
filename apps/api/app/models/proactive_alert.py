from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProactiveAlertRecord(Base):
    __tablename__ = "proactive_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="proactive_monitor")
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="generated", index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="medium", index=True)

    day_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    slot_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    location_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    alternatives: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    freshness_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    resolution_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

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
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)