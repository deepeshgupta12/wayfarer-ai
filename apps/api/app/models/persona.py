from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TravellerPersonaRecord(Base):
    __tablename__ = "traveller_personas"

    traveller_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    archetype: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    travel_style: Mapped[str] = mapped_column(String(50), nullable=False)
    pace_preference: Mapped[str] = mapped_column(String(50), nullable=False)
    group_type: Mapped[str] = mapped_column(String(50), nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSON, nullable=False)