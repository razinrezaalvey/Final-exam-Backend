"""Parcel schemas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.models.parcel import DeliveryStatus, ParcelType, PaymentStatus


class ParcelCreateRequest(BaseModel):
    sender_name: str = Field(min_length=1, max_length=150)
    sender_phone: str = Field(min_length=7, max_length=30)
    sender_address: str = Field(min_length=5, max_length=500)

    receiver_name: str = Field(min_length=1, max_length=150)
    receiver_phone: str = Field(min_length=7, max_length=30)
    receiver_address: str = Field(min_length=5, max_length=500)

    pickup_address: str = Field(min_length=5, max_length=500)
    delivery_address: str = Field(min_length=5, max_length=500)

    parcel_type: ParcelType = ParcelType.small_package
    parcel_weight: float = Field(gt=0, le=1000, description="Weight in kilograms")
    parcel_description: str | None = Field(default=None, max_length=1000)
    special_instruction: str | None = Field(default=None, max_length=500)

    cod_amount: float = Field(default=0.0, ge=0, description="Cash-on-delivery amount")


class ParcelUpdateRequest(BaseModel):
    """Admin can update parcel details before it is picked up."""
    sender_name: str | None = Field(default=None, min_length=1, max_length=150)
    sender_phone: str | None = Field(default=None, min_length=7, max_length=30)
    sender_address: str | None = Field(default=None, min_length=5, max_length=500)
    receiver_name: str | None = Field(default=None, min_length=1, max_length=150)
    receiver_phone: str | None = Field(default=None, min_length=7, max_length=30)
    receiver_address: str | None = Field(default=None, min_length=5, max_length=500)
    pickup_address: str | None = Field(default=None, min_length=5, max_length=500)
    delivery_address: str | None = Field(default=None, min_length=5, max_length=500)
    special_instruction: str | None = Field(default=None, max_length=500)


class ParcelStatusUpdateRequest(BaseModel):
    new_status: DeliveryStatus
    note: str | None = Field(default=None, max_length=500)


class ParcelResponse(BaseModel):
    id: int
    tracking_number: str
    customer_id: int
    agent_id: int | None
    sender_name: str
    sender_phone: str
    sender_address: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    pickup_address: str
    delivery_address: str
    parcel_type: ParcelType
    parcel_weight: float
    parcel_description: str | None
    special_instruction: str | None
    delivery_charge: float
    cod_amount: float
    payment_status: PaymentStatus
    delivery_status: DeliveryStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TrackingResponse(BaseModel):
    tracking_number: str
    delivery_status: DeliveryStatus
    sender_name: str
    receiver_name: str
    pickup_address: str
    delivery_address: str
    history: list["StatusHistoryResponse"]

    model_config = {"from_attributes": True}


class StatusHistoryResponse(BaseModel):
    id: int
    old_status: str | None
    new_status: str
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


TrackingResponse.model_rebuild()
