"""FastAPI dependencies — authentication, DB session, rate limiting."""

from datetime import datetime, timezone

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.core.security import ALGORITHM, ACCESS_TOKEN_TYPE, hash_jti
from app.database import get_db
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate Bearer token and return the authenticated user."""
    if credentials is None:
        raise UnauthorizedError("Authorization header missing.")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired access token.")

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type.")

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token subject missing.")

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise UnauthorizedError("Invalid token subject.")

    user: User | None = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError("User not found.")

    if not user.is_active:
        raise ForbiddenError("Account is deactivated.")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Alias for get_current_user; ensures user is active (already checked)."""
    return current_user


def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that ensures the current user is an admin."""
    if current_user.role != UserRole.admin:
        raise ForbiddenError("Admin access required.")
    return current_user


def require_agent(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that ensures the current user is a delivery agent."""
    if current_user.role != UserRole.agent:
        raise ForbiddenError("Agent access required.")
    return current_user


def require_customer(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that ensures the current user is a customer."""
    if current_user.role != UserRole.customer:
        raise ForbiddenError("Customer access required.")
    return current_user


def require_admin_or_agent(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role not in (UserRole.admin, UserRole.agent):
        raise ForbiddenError("Admin or agent access required.")
    return current_user


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
