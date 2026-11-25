"""Parcel model."""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, ForeignKey, Index, Numeric, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParcelType(str, enum.Enum):
    document = "document"
    small_package = "small_package"
    medium_package = "medium_package"
    large_package = "large_package"
    fragile = "fragile"
    perishable = "perishable"


class DeliveryStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    assigned = "assigned"
    picked_up = "picked_up"
    in_transit = "in_transit"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    cancelled = "cancelled"
    returned = "returned"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    refunded = "refunded"
    failed = "failed"


VALID_STATUS_TRANSITIONS: dict[DeliveryStatus, list[DeliveryStatus]] = {
    DeliveryStatus.pending: [DeliveryStatus.confirmed, DeliveryStatus.cancelled],
    DeliveryStatus.confirmed: [DeliveryStatus.assigned, DeliveryStatus.cancelled],
    DeliveryStatus.assigned: [DeliveryStatus.picked_up, DeliveryStatus.cancelled],
    DeliveryStatus.picked_up: [DeliveryStatus.in_transit],
    DeliveryStatus.in_transit: [DeliveryStatus.out_for_delivery],
    DeliveryStatus.out_for_delivery: [DeliveryStatus.delivered, DeliveryStatus.failed],
    DeliveryStatus.delivered: [],
    DeliveryStatus.failed: [DeliveryStatus.returned],
    DeliveryStatus.cancelled: [],
    DeliveryStatus.returned: [],
}


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tracking_number: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    sender_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sender_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    sender_address: Mapped[str] = mapped_column(String(500), nullable=False)

    receiver_name: Mapped[str] = mapped_column(String(150), nullable=False)
    receiver_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    receiver_address: Mapped[str] = mapped_column(String(500), nullable=False)

    pickup_address: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_address: Mapped[str] = mapped_column(String(500), nullable=False)

    parcel_type: Mapped[ParcelType] = mapped_column(
        Enum(ParcelType), nullable=False, default=ParcelType.small_package
    )
    parcel_weight: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    parcel_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    special_instruction: Mapped[str | None] = mapped_column(Text, nullable=True)

    delivery_charge: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    cod_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending, index=True
    )
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), nullable=False, default=DeliveryStatus.pending, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    customer: Mapped["User"] = relationship(
        "User", foreign_keys=[customer_id], back_populates="parcels"
    )
    agent: Mapped["User | None"] = relationship(
        "User", foreign_keys=[agent_id], lazy="select"
    )
    status_history: Mapped[list["ParcelStatusHistory"]] = relationship(
        "ParcelStatusHistory", back_populates="parcel", order_by="ParcelStatusHistory.created_at", lazy="select"
    )
    assignments: Mapped[list["AgentAssignment"]] = relationship(
        "AgentAssignment", back_populates="parcel", lazy="select"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="parcel", lazy="select"
    )
    review: Mapped["Review | None"] = relationship(
        "Review", back_populates="parcel", uselist=False, lazy="select"
    )

    __table_args__ = (
        Index("ix_parcels_customer_status", "customer_id", "delivery_status"),
        Index("ix_parcels_agent_status", "agent_id", "delivery_status"),
    )

    def __repr__(self) -> str:
        return f"<Parcel id={self.id} tracking={self.tracking_number} status={self.delivery_status}>"
