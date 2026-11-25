"""Admin service — dashboard statistics, reports, settings management."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.parcel import DeliveryStatus, Parcel
from app.models.payment import Payment, PaymentStatusEnum
from app.models.platform_setting import PlatformSetting
from app.models.user import User, UserRole
from app.schemas.misc import DashboardStats, PlatformSettingUpdateRequest


def get_dashboard_stats(db: Session) -> DashboardStats:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_customers = db.query(func.count(User.id)).filter(User.role == UserRole.customer).scalar() or 0
    total_agents = db.query(func.count(User.id)).filter(User.role == UserRole.agent).scalar() or 0
    total_parcels = db.query(func.count(Parcel.id)).scalar() or 0
    pending_parcels = db.query(func.count(Parcel.id)).filter(
        Parcel.delivery_status == DeliveryStatus.pending
    ).scalar() or 0
    active_deliveries = db.query(func.count(Parcel.id)).filter(
        Parcel.delivery_status.in_([
            DeliveryStatus.assigned,
            DeliveryStatus.picked_up,
            DeliveryStatus.in_transit,
            DeliveryStatus.out_for_delivery,
        ])
    ).scalar() or 0
    delivered_parcels = db.query(func.count(Parcel.id)).filter(
        Parcel.delivery_status == DeliveryStatus.delivered
    ).scalar() or 0
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.payment_status == PaymentStatusEnum.completed
    ).scalar() or 0.0

    return DashboardStats(
        total_users=total_users,
        total_customers=total_customers,
        total_agents=total_agents,
        total_parcels=total_parcels,
        pending_parcels=pending_parcels,
        active_deliveries=active_deliveries,
        delivered_parcels=delivered_parcels,
        total_revenue=float(total_revenue),
    )


def list_audit_logs(
    db: Session,
    *,
    user_id: int | None = None,
    action: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    total = query.count()
    items = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_all_settings(db: Session) -> list[PlatformSetting]:
    return db.query(PlatformSetting).order_by(PlatformSetting.setting_key).all()


def get_setting(db: Session, key: str) -> PlatformSetting:
    setting = db.query(PlatformSetting).filter(
        PlatformSetting.setting_key == key
    ).first()
    if setting is None:
        raise NotFoundError(f"Setting '{key}'")
    return setting


def upsert_setting(
    db: Session, key: str, data: PlatformSettingUpdateRequest
) -> PlatformSetting:
    setting = db.query(PlatformSetting).filter(
        PlatformSetting.setting_key == key
    ).first()
    if setting is None:
        setting = PlatformSetting(setting_key=key, setting_value=data.setting_value)
        db.add(setting)
    else:
        setting.setting_value = data.setting_value
    db.commit()
    db.refresh(setting)
    return setting


def list_notifications(
    db: Session,
    *,
    user_id: int | None = None,
    is_read: bool | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Notification], int]:
    query = db.query(Notification)
    if user_id:
        query = query.filter(Notification.user_id == user_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    total = query.count()
    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def mark_notification_read(db: Session, notification_id: int, user_id: int) -> Notification:
    notif = db.get(Notification, notification_id)
    if notif is None:
        raise NotFoundError("Notification")
    if notif.user_id != user_id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError()
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif
