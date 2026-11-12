from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import random
import string
from datetime import datetime, timezone

from deps import get_db
from router.auth import get_current_user
import models

router = APIRouter()


def generate_tracking_number() -> str:
    prefix = "SC"
    suffix = "".join(random.choices(string.digits, k=8))
    return f"{prefix}{suffix}"


def parcel_dict(p: models.Parcel) -> dict:
    status_val = p.status or "pending"
    weight = p.parcel_weight or 1.0
    charge = 60.0 + max(0.0, (weight - 1.0) * 20.0)

    return {
        "id": p.id,
        "tracking_number": p.tracking_number,
        "sender_name": p.sender_name,
        "sender_phone": p.sender_phone,
        "sender_address": p.sender_address,
        "receiver_name": p.receiver_name,
        "receiver_phone": p.receiver_phone,
        "receiver_address": p.receiver_address,
        "pickup_address": p.pickup_address or p.sender_address,
        "delivery_address": p.delivery_address or p.receiver_address,
        "parcel_type": p.parcel_type,
        "parcel_weight": p.parcel_weight,
        "weight_kg": p.parcel_weight,
        "cod_amount": p.cod_amount or 0.0,
        "delivery_charge": round(charge, 2),
        "status": status_val,
        "delivery_status": status_val,
        "created_by": p.created_by,
        "agent_id": p.assigned_agent_id,
        "assigned_agent_id": p.assigned_agent_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


class CreateParcelRequest(BaseModel):
    sender_name: str
    sender_phone: str
    sender_address: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    pickup_address: Optional[str] = None
    delivery_address: Optional[str] = None
    parcel_type: Optional[str] = None
    parcel_weight: Optional[float] = 1.0
    cod_amount: Optional[float] = 0.0
    special_instruction: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: Optional[str] = None
    new_status: Optional[str] = None
    note: Optional[str] = None


@router.get("/parcels")
def list_parcels(
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Parcel)
    if current_user.role == "customer":
        query = query.filter(models.Parcel.created_by == current_user.id)
    elif current_user.role == "agent":
        query = query.filter(models.Parcel.assigned_agent_id == current_user.id)

    parcels = query.order_by(models.Parcel.created_at.desc()).limit(page_size).all()
    data = [parcel_dict(p) for p in parcels]
    return {"success": True, "data": data}


@router.post("/parcels", status_code=201)
def create_parcel(
    body: CreateParcelRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    tracking = generate_tracking_number()
    while db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking).first():
        tracking = generate_tracking_number()

    parcel = models.Parcel(
        tracking_number=tracking,
        sender_name=body.sender_name,
        sender_phone=body.sender_phone,
        sender_address=body.sender_address,
        receiver_name=body.receiver_name,
        receiver_phone=body.receiver_phone,
        receiver_address=body.receiver_address,
        pickup_address=body.pickup_address or body.sender_address,
        delivery_address=body.delivery_address or body.receiver_address,
        parcel_type=body.parcel_type,
        parcel_weight=body.parcel_weight,
        cod_amount=body.cod_amount or 0.0,
        status="pending",
        created_by=current_user.id,
    )
    db.add(parcel)
    db.commit()
    db.refresh(parcel)

    d = parcel_dict(parcel)
    return {**d, "success": True, "data": d}


@router.patch("/parcels/{parcel_id}/status")
def update_parcel_status(
    parcel_id: int,
    body: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    parcel = db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    new_st = body.new_status or body.status
    if new_st:
        prev_st = parcel.status
        parcel.status = new_st
        parcel.updated_at = datetime.now(timezone.utc)

        # If marked delivered, credit agent
        if new_st == "delivered" and prev_st != "delivered" and parcel.assigned_agent_id:
            profile = db.query(models.AgentProfile).filter(
                models.AgentProfile.user_id == parcel.assigned_agent_id
            ).first()
            if profile:
                profile.total_deliveries = (profile.total_deliveries or 0) + 1
                profile.total_earnings = (profile.total_earnings or 0.0) + 80.0

        db.commit()
        db.refresh(parcel)

    d = parcel_dict(parcel)
    return {**d, "success": True, "data": d}


@router.get("/tracking/{tracking_number}")
def track_parcel(tracking_number: str, db: Session = Depends(get_db)):
    parcel = db.query(models.Parcel).filter(models.Parcel.tracking_number == tracking_number).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    d = parcel_dict(parcel)
    history = [
        {
            "new_status": parcel.status or "pending",
            "note": f"Parcel { (parcel.status or 'pending').replace('_', ' ') }",
            "created_at": parcel.updated_at.isoformat() if parcel.updated_at else parcel.created_at.isoformat() if parcel.created_at else None,
        }
    ]
    d["history"] = history
    return {**d, "success": True, "data": d}
