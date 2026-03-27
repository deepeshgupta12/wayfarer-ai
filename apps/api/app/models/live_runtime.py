from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ActiveTripContextRecord(Base):
    __tablename__ = "active_trip_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="live_runtime")
    trip_status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    intent_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transport_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget_level_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    available_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_day_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_slot_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)

    local_time_iso: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_place_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_country: Mapped[str | None] = mapped_column(String(255), nullable=True)

    context_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

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


class AgentGraphRunRecord(Base):
    __tablename__ = "agent_graph_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    planning_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    source_surface: Mapped[str] = mapped_column(String(100), nullable=False, default="live_runtime")
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running")
    routed_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supervisor_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkpoint_thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    graph_state: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    final_output: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

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


class AgentGraphEventRecord(Base):
    __tablename__ = "agent_graph_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    traveller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trip_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )