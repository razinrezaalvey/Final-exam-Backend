from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from deps import get_db, hash_password, verify_password
from router.auth import get_current_user
import models

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreateUserRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "agent"
    password: str


class UpdateUserStatusRequest(BaseModel):
    is_active: Optional[bool] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None


def user_dict(user: models.User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("/me")
def get_me(current_user: models.User = Depends(get_current_user)):
    d = user_dict(current_user)
    return {**d, "success": True, "data": d}


@router.put("/me")
def update_me(
    body: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    db.commit()
    db.refresh(current_user)
    d = user_dict(current_user)
    return {**d, "success": True, "data": d}


@router.post("/me/change-password")
@router.put("/me/change-password")
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"success": True, "message": "Password changed successfully"}


@router.get("")
def list_users(
    role: Optional[str] = None,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    query = db.query(models.User)
    if role:
        query = query.filter(models.User.role == role)
    users = query.limit(page_size).all()
    return {"success": True, "data": [user_dict(u) for u in users]}


@router.post("", status_code=201)
def create_user(
    body: CreateUserRequest,
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
        role=body.role,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if user.role == "agent":
        db.add(models.AgentProfile(user_id=user.id))
        db.commit()

    d = user_dict(user)
    return {**d, "success": True, "data": d}


@router.put("/{user_id}")
def update_user_status(
    user_id: int,
    body: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    if body.role is not None:
        user.role = body.role

    db.commit()
    db.refresh(user)
    d = user_dict(user)
    return {**d, "success": True, "data": d}
