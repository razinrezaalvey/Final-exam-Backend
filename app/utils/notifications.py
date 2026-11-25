"""Notification utility."""

from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationType


def create_notification(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: NotificationType = NotificationType.system,
) -> Notification:
    """Create and persist a notification. Does NOT commit — caller commits."""
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
    )
    db.add(notif)
    return notif
