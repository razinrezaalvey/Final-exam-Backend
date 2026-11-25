"""Review model."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    customer: Mapped["User"] = relationship("User", back_populates="reviews")
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="review")

    __table_args__ = (
        UniqueConstraint("customer_id", "parcel_id", name="uq_review_customer_parcel"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    def __repr__(self) -> str:
        return f"<Review id={self.id} parcel={self.parcel_id} rating={self.rating}>"
