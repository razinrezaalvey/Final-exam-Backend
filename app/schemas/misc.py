"""Payment, Review, Notification, and AuditLog schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.payment import PaymentMethod, PaymentStatusEnum
from app.models.notification import NotificationType


class PaymentCreateRequest(BaseModel):
    parcel_id: int
    payment_method: PaymentMethod
    idempotency_key: str | None = Field(default=None, max_length=255)


class PaymentResponse(BaseModel):
    id: int
    customer_id: int
    parcel_id: int
    amount: float
    payment_method: PaymentMethod
    transaction_id: str | None
    payment_status: PaymentStatusEnum
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreateRequest(BaseModel):
    parcel_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewResponse(BaseModel):
    id: int
    customer_id: int
    parcel_id: int
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: int | None
    details: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformSettingResponse(BaseModel):
    id: int
    setting_key: str
    setting_value: str
    description: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformSettingUpdateRequest(BaseModel):
    setting_value: str = Field(min_length=1)


class DashboardStats(BaseModel):
    total_users: int
    total_customers: int
    total_agents: int
    total_parcels: int
    pending_parcels: int
    active_deliveries: int
    delivered_parcels: int
    total_revenue: float
