from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from deps import get_db, hash_password
from router.auth import get_current_user
import models

router = APIRouter()


class UpdateAgentProfileRequest(BaseModel):
    vehicle_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    license_number: Optional[str] = None
    availability_status: Optional[str] = None


class CreateAgentRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    vehicle_type: Optional[str] = "motorcycle"
    vehicle_number: Optional[str] = ""
    license_number: Optional[str] = ""


class AssignParcelRequest(BaseModel):
    parcel_id: int
    agent_id: int
    note: Optional[str] = None


def profile_dict(profile: models.AgentProfile, user: models.User) -> dict:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "vehicle_type": profile.vehicle_type or "motorcycle",
        "vehicle_number": profile.vehicle_number or "",
        "license_number": profile.license_number or "",
        "availability_status": profile.availability_status or "available",
        "total_deliveries": profile.total_deliveries or 0,
        "total_earnings": profile.total_earnings or 0.0,
    }


@router.get("/me/profile")
def get_agent_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Agents only")
    profile = db.query(models.AgentProfile).filter(
        models.AgentProfile.user_id == current_user.id
    ).first()
    if not profile:
        profile = models.AgentProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    d = profile_dict(profile, current_user)
    return {**d, "success": True, "data": d}


@router.put("/me/profile")
def update_agent_profile(
    body: UpdateAgentProfileRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "agent":
        raise HTTPException(status_code=403, detail="Agents only")
    profile = db.query(models.AgentProfile).filter(
        models.AgentProfile.user_id == current_user.id
    ).first()
    if not profile:
        profile = models.AgentProfile(user_id=current_user.id)
        db.add(profile)

    if body.vehicle_type is not None:
        profile.vehicle_type = body.vehicle_type
    if body.vehicle_number is not None:
        profile.vehicle_number = body.vehicle_number
    if body.license_number is not None:
        profile.license_number = body.license_number
    if body.availability_status is not None:
        profile.availability_status = body.availability_status

    db.commit()
    db.refresh(profile)

    d = profile_dict(profile, current_user)
    return {**d, "success": True, "data": d}


@router.post("", status_code=201)
def create_agent(
    body: CreateAgentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        hashed_password=hash_password(body.password),
        role="agent",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = models.AgentProfile(
        user_id=user.id,
        vehicle_type=body.vehicle_type,
        vehicle_number=body.vehicle_number,
        license_number=body.license_number,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    d = profile_dict(profile, user)
    return {**d, "success": True, "data": d}


@router.post("/assignments")
def assign_parcel(
    body: AssignParcelRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")

    parcel = db.query(models.Parcel).filter(models.Parcel.id == body.parcel_id).first()
    if not parcel:
        raise HTTPException(status_code=404, detail="Parcel not found")

    agent = db.query(models.User).filter(
        models.User.id == body.agent_id, models.User.role == "agent"
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    parcel.assigned_agent_id = agent.id
    parcel.status = "assigned"
    db.commit()

    return {"success": True, "message": "Parcel assigned to agent"}
