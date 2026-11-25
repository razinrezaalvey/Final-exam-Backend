"""AgentProfile model."""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, ForeignKey, Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VehicleType(str, enum.Enum):
    bicycle = "bicycle"
    motorcycle = "motorcycle"
    car = "car"
    van = "van"
    truck = "truck"


class AvailabilityStatus(str, enum.Enum):
    available = "available"
    busy = "busy"
    offline = "offline"


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    vehicle_type: Mapped[VehicleType | None] = mapped_column(
        Enum(VehicleType), nullable=True
    )
    vehicle_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus),
        nullable=False,
        default=AvailabilityStatus.offline,
    )
    total_deliveries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_earnings: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="agent_profile")

    def __repr__(self) -> str:
        return f"<AgentProfile id={self.id} user_id={self.user_id}>"
