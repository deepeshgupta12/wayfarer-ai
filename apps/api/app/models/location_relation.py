from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocationRelationRecord(Base):
    __tablename__ = "location_relations"

    relation_id: Mapped[str] = mapped_column(String(512), primary_key=True)
    source_location_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_city: Mapped[str] = mapped_column(String(255), nullable=False)
    source_country: Mapped[str] = mapped_column(String(255), nullable=False)

    target_location_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_country: Mapped[str] = mapped_column(String(255), nullable=False)
    target_category: Mapped[str] = mapped_column(String(100), nullable=False)

    relation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    relation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    city_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    destination_context: Mapped[str] = mapped_column(String(255), nullable=False)

    target_rating: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    relation_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)