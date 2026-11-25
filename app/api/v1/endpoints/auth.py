"""Authentication endpoints."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BadRequestError
from app.database import get_db
from app.dependencies import get_current_active_user, get_client_ip
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest, LogoutRequest, RefreshRequest,
    ResetPasswordRequest, TokenResponse, VerifyEmailRequest,
)
from app.schemas.common import SuccessResponse
from app.schemas.user import UserRegisterRequest, UserLoginRequest, UserResponse
from app.services import auth_service
from app.utils.audit import log_action
from app.utils.notifications import create_notification
from app.models.notification import NotificationType

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: UserRegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new customer account."""
    user = auth_service.register_user(db, data)
    verification_token = auth_service.generate_email_verification_token(db, user)
    if settings.DEBUG:
        request.state.verification_token = verification_token

    log_action(
        db,
        user_id=user.id,
        action="user.register",
        resource_type="User",
        resource_id=user.id,
        ip_address=get_client_ip(request),
    )
    create_notification(
        db,
        user_id=user.id,
        title="Welcome to SwiftCourier!",
        message="Your account has been created. Please verify your email.",
        notification_type=NotificationType.account,
    )
    db.commit()
    return user


@router.post("/login")
def login(
    data: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate and receive access + refresh tokens."""
    user = auth_service.authenticate_user(db, data.email, data.password)
    access_token, refresh_token = auth_service.create_token_pair(db, user)

    log_action(
        db,
        user_id=user.id,
        action="user.login",
        resource_type="User",
        resource_id=user.id,
        ip_address=get_client_ip(request),
    )
    db.commit()

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value,
                "is_verified": user.is_verified,
            },
        },
    }


@router.post("/refresh")
def refresh_token(
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue a new access token."""
    access_token, new_refresh_token, user = auth_service.rotate_refresh_token(
        db, data.refresh_token
    )
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        },
    }


@router.post("/logout", response_model=SuccessResponse)
def logout(
    data: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Revoke the refresh token (logout)."""
    auth_service.revoke_refresh_token(db, data.refresh_token)
    log_action(
        db,
        user_id=current_user.id,
        action="user.logout",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return SuccessResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/forgot-password", response_model=SuccessResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Initiate password reset.
    Always returns 200 to prevent email enumeration.
    In production, sends the token via email.
    """
    raw_token = auth_service.initiate_password_reset(db, data.email)
    response_data: dict = {"message": "If the email exists, a reset link has been sent."}
    if settings.DEBUG and raw_token:
        response_data["debug_reset_token"] = raw_token
    return SuccessResponse(**{"message": response_data["message"]})


@router.post("/reset-password", response_model=SuccessResponse)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Complete password reset using the secure token."""
    auth_service.complete_password_reset(db, data.token, data.new_password)
    return SuccessResponse(message="Password has been reset successfully.")


@router.post("/verify-email", response_model=SuccessResponse)
def verify_email(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    """Verify email address using the verification token."""
    auth_service.verify_user_email(db, data.token)
    return SuccessResponse(message="Email verified successfully.")

