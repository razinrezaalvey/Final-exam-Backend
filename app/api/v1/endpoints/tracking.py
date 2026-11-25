"""Tracking endpoint — public parcel tracking by tracking number."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.parcel import TrackingResponse, StatusHistoryResponse
from app.services import parcel_service

router = APIRouter(prefix="/tracking", tags=["Tracking"])


@router.get("/{tracking_number}", response_model=TrackingResponse)
def track_parcel(
    tracking_number: str,
    db: Session = Depends(get_db),
):
    """
    Public endpoint: track a parcel by its tracking number.
    Returns delivery status and status history.
    No authentication required.
    """
    parcel = parcel_service.get_parcel_by_tracking(db, tracking_number.strip().upper())
    return TrackingResponse(
        tracking_number=parcel.tracking_number,
        delivery_status=parcel.delivery_status,
        sender_name=parcel.sender_name,
        receiver_name=parcel.receiver_name,
        pickup_address=parcel.pickup_address,
        delivery_address=parcel.delivery_address,
        history=[
            StatusHistoryResponse.model_validate(h)
            for h in parcel.status_history
        ],
    )

