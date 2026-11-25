"""AgentAssignment model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssignmentStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    cancelled = "cancelled"


class AgentAssignment(Base):
    __tablename__ = "agent_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assignment_status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus), nullable=False, default=AssignmentStatus.pending, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="assignments")
    agent_user: Mapped["User"] = relationship(
        "User", foreign_keys=[agent_id], back_populates="agent_assignments"
    )
    assigner: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return f"<AgentAssignment id={self.id} parcel={self.parcel_id} agent={self.agent_id}>"
