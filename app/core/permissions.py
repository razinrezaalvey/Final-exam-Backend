"""RBAC permission helpers."""

from functools import wraps
from app.models.user import UserRole
from app.core.exceptions import ForbiddenError


def require_roles(*roles: UserRole):
    """
    Dependency factory: raise 403 if current user's role is not in `roles`.

    Usage:
        @router.get("/admin-only")
        def endpoint(current_user: User = Depends(get_current_active_user)):
            require_role_check(current_user, UserRole.admin)
    """
    def check(user) -> None:
        if user.role not in roles:
            raise ForbiddenError()
    return check


def is_admin(user) -> bool:
    return user.role == UserRole.admin


def is_agent(user) -> bool:
    return user.role == UserRole.agent


def is_customer(user) -> bool:
    return user.role == UserRole.customer


def assert_admin(user) -> None:
    if not is_admin(user):
        raise ForbiddenError("Admin access required.")


def assert_agent(user) -> None:
    if not is_agent(user):
        raise ForbiddenError("Agent access required.")


def assert_customer(user) -> None:
    if not is_customer(user):
        raise ForbiddenError("Customer access required.")


def assert_admin_or_agent(user) -> None:
    if user.role not in (UserRole.admin, UserRole.agent):
        raise ForbiddenError("Admin or agent access required.")
