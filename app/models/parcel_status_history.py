"""ParcelStatusHistory model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParcelStatusHistory(Base):
    __tablename__ = "parcel_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    old_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="status_history")
    updated_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by])

    def __repr__(self) -> str:
        return f"<ParcelStatusHistory parcel_id={self.parcel_id} {self.old_status}->{self.new_status}>"
