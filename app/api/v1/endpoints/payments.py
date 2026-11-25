"""Payment endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse
from app.schemas.misc import PaymentCreateRequest, PaymentResponse
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Customer: initiate payment for a parcel."""
    from app.core.exceptions import ForbiddenError
    if current_user.role != UserRole.customer:
        raise ForbiddenError("Only customers can initiate payments.")
    return payment_service.create_payment(db, data, current_user)


@router.get("/me", response_model=PaginatedResponse[PaymentResponse])
def list_my_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Customer: list own payment history."""
    skip = (page - 1) * page_size
    items, total = payment_service.list_payments(
        db, customer_id=current_user.id, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[PaymentResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=PaginatedResponse[PaymentResponse])
def list_all_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    customer_id: int | None = Query(default=None),
    parcel_id: int | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: list all payments."""
    skip = (page - 1) * page_size
    items, total = payment_service.list_payments(
        db, customer_id=customer_id, parcel_id=parcel_id, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[PaymentResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )

