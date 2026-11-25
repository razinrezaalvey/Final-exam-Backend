"""Payment service."""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.parcel import Parcel, PaymentStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatusEnum
from app.models.user import User
from app.schemas.misc import PaymentCreateRequest


def create_payment(db: Session, data: PaymentCreateRequest, customer: User) -> Payment:
    """
    Initiate a payment for a parcel.

    For COD: records payment as pending (completed on delivery).
    For online: mock provider simulation — in production, integrate a real gateway.
    """
    parcel: Parcel | None = db.get(Parcel, data.parcel_id)
    if parcel is None:
        raise NotFoundError("Parcel")

    if parcel.customer_id != customer.id:
        raise ForbiddenError("You do not own this parcel.")

    if data.idempotency_key:
        existing = db.query(Payment).filter(
            Payment.idempotency_key == data.idempotency_key
        ).first()
        if existing:
            return existing

    completed = db.query(Payment).filter(
        Payment.parcel_id == data.parcel_id,
        Payment.payment_status == PaymentStatusEnum.completed,
    ).first()
    if completed:
        raise ConflictError("This parcel has already been paid.")

    idempotency_key = data.idempotency_key or str(uuid.uuid4())

    if data.payment_method == PaymentMethod.cash_on_delivery:
        payment = Payment(
            customer_id=customer.id,
            parcel_id=data.parcel_id,
            amount=float(parcel.delivery_charge) + float(parcel.cod_amount),
            payment_method=data.payment_method,
            idempotency_key=idempotency_key,
            payment_status=PaymentStatusEnum.pending,
        )
    else:
        transaction_id = f"MOCK-TXN-{uuid.uuid4().hex[:12].upper()}"
        payment = Payment(
            customer_id=customer.id,
            parcel_id=data.parcel_id,
            amount=float(parcel.delivery_charge),
            payment_method=data.payment_method,
            transaction_id=transaction_id,
            idempotency_key=idempotency_key,
            payment_status=PaymentStatusEnum.completed,
        )
        parcel.payment_status = PaymentStatus.paid

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def list_payments(
    db: Session,
    *,
    customer_id: int | None = None,
    parcel_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Payment], int]:
    query = db.query(Payment)
    if customer_id:
        query = query.filter(Payment.customer_id == customer_id)
    if parcel_id:
        query = query.filter(Payment.parcel_id == parcel_id)
    total = query.count()
    items = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    return items, total
