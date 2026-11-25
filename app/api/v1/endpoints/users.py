"""User management endpoints."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user, require_admin, get_client_ip
from app.models.user import User, UserRole
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.user import (
    AdminCreateUserRequest, AdminUpdateUserRequest,
    ChangePasswordRequest, UserResponse, UserUpdateRequest,
)
from app.services import user_service
from app.utils.audit import log_action

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_active_user)):
    """Get current user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_my_profile(
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    return user_service.update_own_profile(db, current_user, data)


@router.post("/me/change-password", response_model=SuccessResponse)
def change_my_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    user_service.change_password(db, current_user, data)
    return SuccessResponse(message="Password updated successfully.")


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: list all users with filtering and pagination."""
    skip = (page - 1) * page_size
    users, total = user_service.list_users(
        db, role=role, is_active=is_active, search=search, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    data: AdminCreateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: create an agent or admin account."""
    user = user_service.admin_create_user(db, data)
    log_action(
        db,
        user_id=admin.id,
        action="admin.create_user",
        resource_type="User",
        resource_id=user.id,
        details=f"Created {user.role} account: {user.email}",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get a user by ID."""
    return user_service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: AdminUpdateUserRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: update a user's information."""
    user = user_service.admin_update_user(db, user_id, data)
    log_action(
        db,
        user_id=admin.id,
        action="admin.update_user",
        resource_type="User",
        resource_id=user_id,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return user

