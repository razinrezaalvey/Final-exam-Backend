"""Payment model."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentMethod(str, enum.Enum):
    cash_on_delivery = "cash_on_delivery"
    online = "online"
    wallet = "wallet"


class PaymentStatusEnum(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod), nullable=False
    )
    transaction_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    payment_status: Mapped[PaymentStatusEnum] = mapped_column(
        Enum(PaymentStatusEnum), nullable=False, default=PaymentStatusEnum.pending
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

    customer: Mapped["User"] = relationship("User", back_populates="payments")
    parcel: Mapped["Parcel"] = relationship("Parcel", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} parcel={self.parcel_id} status={self.payment_status}>"
