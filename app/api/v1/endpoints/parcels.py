"""Parcel management endpoints."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin, get_client_ip
from app.models.parcel import DeliveryStatus
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.parcel import (
    ParcelCreateRequest, ParcelResponse, ParcelStatusUpdateRequest,
    ParcelUpdateRequest, StatusHistoryResponse, TrackingResponse,
)
from app.services import parcel_service
from app.utils.audit import log_action
from app.utils.notifications import create_notification
from app.models.notification import NotificationType

router = APIRouter(prefix="/parcels", tags=["Parcels"])


@router.post("", response_model=ParcelResponse, status_code=status.HTTP_201_CREATED)
def create_parcel(
    data: ParcelCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Customer: create a new parcel delivery request."""
    from app.core.exceptions import ForbiddenError
    if current_user.role != UserRole.customer:
        raise ForbiddenError("Only customers can create parcels.")

    parcel = parcel_service.create_parcel(db, data, current_user)
    log_action(
        db,
        user_id=current_user.id,
        action="parcel.create",
        resource_type="Parcel",
        resource_id=parcel.id,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return parcel


@router.get("", response_model=PaginatedResponse[ParcelResponse])
def list_parcels(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: DeliveryStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List parcels.
    - Customer: sees only their own parcels.
    - Agent: sees only parcels assigned to them.
    - Admin: sees all parcels.
    """
    skip = (page - 1) * page_size
    kwargs: dict = {"status": status_filter, "search": search, "skip": skip, "limit": page_size}

    if current_user.role == UserRole.customer:
        kwargs["customer_id"] = current_user.id
    elif current_user.role == UserRole.agent:
        kwargs["agent_id"] = current_user.id

    parcels, total = parcel_service.list_parcels(db, **kwargs)
    return PaginatedResponse.build(
        data=[ParcelResponse.model_validate(p) for p in parcels],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{parcel_id}", response_model=ParcelResponse)
def get_parcel(
    parcel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get parcel details — enforces ownership for customers/agents."""
    from app.core.exceptions import ForbiddenError
    parcel = parcel_service.get_parcel_by_id(db, parcel_id)

    if current_user.role == UserRole.customer and parcel.customer_id != current_user.id:
        raise ForbiddenError("You do not have access to this parcel.")
    if current_user.role == UserRole.agent and parcel.agent_id != current_user.id:
        raise ForbiddenError("This parcel is not assigned to you.")

    return parcel


@router.get("/{parcel_id}/history", response_model=list[StatusHistoryResponse])
def get_parcel_history(
    parcel_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get status history of a parcel."""
    from app.core.exceptions import ForbiddenError
    parcel = parcel_service.get_parcel_by_id(db, parcel_id)

    if current_user.role == UserRole.customer and parcel.customer_id != current_user.id:
        raise ForbiddenError("You do not have access to this parcel.")
    if current_user.role == UserRole.agent and parcel.agent_id != current_user.id:
        raise ForbiddenError("This parcel is not assigned to you.")

    return parcel.status_history


@router.patch("/{parcel_id}/status", response_model=ParcelResponse)
def update_parcel_status(
    parcel_id: int,
    data: ParcelStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update parcel delivery status (role-based transition rules apply)."""
    parcel = parcel_service.get_parcel_by_id(db, parcel_id)
    updated = parcel_service.update_parcel_status(db, parcel, data, current_user)

    log_action(
        db,
        user_id=current_user.id,
        action="parcel.status_update",
        resource_type="Parcel",
        resource_id=parcel_id,
        details=f"Status changed to {data.new_status}",
        ip_address=get_client_ip(request),
    )
    create_notification(
        db,
        user_id=updated.customer_id,
        title="Parcel Status Updated",
        message=f"Your parcel {updated.tracking_number} is now '{data.new_status.value}'.",
        notification_type=NotificationType.parcel_update,
    )
    db.commit()
    return updated


@router.put("/{parcel_id}", response_model=ParcelResponse)
def admin_update_parcel(
    parcel_id: int,
    data: ParcelUpdateRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: update parcel details (only before pickup)."""
    parcel = parcel_service.get_parcel_by_id(db, parcel_id)
    updated = parcel_service.admin_update_parcel(db, parcel, data)
    log_action(
        db,
        user_id=admin.id,
        action="admin.update_parcel",
        resource_type="Parcel",
        resource_id=parcel_id,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return updated

