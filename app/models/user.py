"""User model."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, Index, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    agent = "agent"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), nullable=False, default=UserRole.customer, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agent_profile: Mapped["AgentProfile"] = relationship(
        "AgentProfile", back_populates="user", uselist=False, lazy="select"
    )
    parcels: Mapped[list["Parcel"]] = relationship(
        "Parcel", foreign_keys="Parcel.customer_id", back_populates="customer", lazy="select"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", lazy="select"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", lazy="select"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="select"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="customer", lazy="select"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="customer", lazy="select"
    )
    agent_assignments: Mapped[list["AgentAssignment"]] = relationship(
        "AgentAssignment", foreign_keys="AgentAssignment.agent_id", back_populates="agent_user", lazy="select"
    )

    __table_args__ = (
        Index("ix_users_role_is_active", "role", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
