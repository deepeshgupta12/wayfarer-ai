from sqlalchemy import Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReviewIntelligenceRecord(Base):
    __tablename__ = "review_intelligence"

    location_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quick_verdict: Mapped[str] = mapped_column(Text, nullable=False)
    themes: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    authenticity_label: Mapped[str] = mapped_column(String(50), nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)