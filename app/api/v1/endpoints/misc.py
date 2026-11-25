"""Reviews, Notifications, Admin, Reports, Settings endpoints."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.misc import (
    AuditLogResponse, DashboardStats,
    NotificationResponse, PlatformSettingResponse,
    PlatformSettingUpdateRequest, ReviewCreateRequest, ReviewResponse,
)
from app.services import admin_service, review_service


reviews_router = APIRouter(prefix="/reviews", tags=["Reviews"])


@reviews_router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    data: ReviewCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Customer: submit a review for a delivered parcel."""
    from app.core.exceptions import ForbiddenError
    if current_user.role != UserRole.customer:
        raise ForbiddenError("Only customers can submit reviews.")
    return review_service.create_review(db, data, current_user)


@reviews_router.get("", response_model=PaginatedResponse[ReviewResponse])
def list_reviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    parcel_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List reviews (customers see their own; admins see all)."""
    skip = (page - 1) * page_size
    customer_id = current_user.id if current_user.role == UserRole.customer else None
    items, total = review_service.list_reviews(
        db, customer_id=customer_id, parcel_id=parcel_id, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[ReviewResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    is_read: bool | None = Query(default=None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user's notifications."""
    skip = (page - 1) * page_size
    items, total = admin_service.list_notifications(
        db, user_id=current_user.id, is_read=is_read, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@notifications_router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    return admin_service.mark_notification_read(db, notification_id, current_user.id)


admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@admin_router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get dashboard statistics."""
    return admin_service.get_dashboard_stats(db)


@admin_router.get("/audit-logs", response_model=PaginatedResponse[AuditLogResponse])
def get_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: view audit logs."""
    skip = (page - 1) * page_size
    items, total = admin_service.list_audit_logs(
        db, user_id=user_id, action=action, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[AuditLogResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


settings_router = APIRouter(prefix="/settings", tags=["Settings"])


@settings_router.get("", response_model=list[PlatformSettingResponse])
def get_all_settings(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get all platform settings."""
    return admin_service.get_all_settings(db)


@settings_router.get("/{key}", response_model=PlatformSettingResponse)
def get_setting(
    key: str,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get a specific platform setting."""
    return admin_service.get_setting(db, key)


@settings_router.put("/{key}", response_model=PlatformSettingResponse)
def upsert_setting(
    key: str,
    data: PlatformSettingUpdateRequest,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: create or update a platform setting."""
    return admin_service.upsert_setting(db, key, data)


reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@reports_router.get("/summary")
def get_summary_report(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get a summary report."""
    from sqlalchemy import func
    from app.models.parcel import Parcel, DeliveryStatus
    from app.models.payment import Payment, PaymentStatusEnum

    stats = admin_service.get_dashboard_stats(db)

    from app.models.parcel import DeliveryStatus as DS
    status_breakdown = {}
    for s in DS:
        count = db.query(func.count(Parcel.id)).filter(
            Parcel.delivery_status == s
        ).scalar() or 0
        status_breakdown[s.value] = count

    return {
        "success": True,
        "data": {
            "overview": stats,
            "parcel_status_breakdown": status_breakdown,
        },
    }

