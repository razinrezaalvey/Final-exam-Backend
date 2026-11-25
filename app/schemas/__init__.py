"""Schemas package — explicit exports."""

from app.schemas.common import PaginationParams, PaginatedResponse, SuccessResponse
from app.schemas.auth import TokenResponse, RefreshRequest, ForgotPasswordRequest, ResetPasswordRequest, VerifyEmailRequest, LogoutRequest
from app.schemas.user import (
    UserRegisterRequest, UserLoginRequest, UserResponse, UserUpdateRequest,
    AdminCreateUserRequest, AdminUpdateUserRequest, ChangePasswordRequest
)
from app.schemas.parcel import (
    ParcelCreateRequest, ParcelUpdateRequest, ParcelStatusUpdateRequest,
    ParcelResponse, TrackingResponse, StatusHistoryResponse
)
from app.schemas.agent import (
    AgentProfileResponse, AgentWithUserResponse, AgentProfileUpdateRequest,
    AdminCreateAgentRequest, AssignmentResponse, AssignParcelRequest, RespondAssignmentRequest
)
from app.schemas.misc import (
    PaymentCreateRequest, PaymentResponse,
    ReviewCreateRequest, ReviewResponse,
    NotificationResponse, AuditLogResponse,
    PlatformSettingResponse, PlatformSettingUpdateRequest,
    DashboardStats
)

__all__ = [
    "PaginationParams", "PaginatedResponse", "SuccessResponse",
    "TokenResponse", "RefreshRequest", "ForgotPasswordRequest", "ResetPasswordRequest",
    "VerifyEmailRequest", "LogoutRequest",
    "UserRegisterRequest", "UserLoginRequest", "UserResponse", "UserUpdateRequest",
    "AdminCreateUserRequest", "AdminUpdateUserRequest", "ChangePasswordRequest",
    "ParcelCreateRequest", "ParcelUpdateRequest", "ParcelStatusUpdateRequest",
    "ParcelResponse", "TrackingResponse", "StatusHistoryResponse",
    "AgentProfileResponse", "AgentWithUserResponse", "AgentProfileUpdateRequest",
    "AdminCreateAgentRequest", "AssignmentResponse", "AssignParcelRequest", "RespondAssignmentRequest",
    "PaymentCreateRequest", "PaymentResponse",
    "ReviewCreateRequest", "ReviewResponse",
    "NotificationResponse", "AuditLogResponse",
    "PlatformSettingResponse", "PlatformSettingUpdateRequest",
    "DashboardStats",
]
