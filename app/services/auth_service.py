"""Authentication service — business logic for auth operations."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import (
    BadRequestError, ConflictError, NotFoundError, UnauthorizedError
)
from app.core.security import (
    create_access_token, create_refresh_token,
    generate_secure_token, hash_jti, hash_password,
    hash_token, verify_password, needs_rehash
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.user import UserRegisterRequest


def register_user(db: Session, data: UserRegisterRequest) -> User:
    """Create a new customer account. Always sets role=customer."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictError("An account with this email address already exists.")

    user = User(
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        phone=data.phone,
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Verify credentials. Returns user or raises."""
    user: User | None = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password.")
    if not user.is_active:
        raise ForbiddenError("Your account has been deactivated.")

    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
        db.commit()

    return user


def create_token_pair(db: Session, user: User) -> tuple[str, str]:
    """Issue a new access+refresh token pair and persist the refresh token."""
    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token, jti = create_refresh_token(subject=user.id)

    expires_at = datetime.now(tz=timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    rt = RefreshToken(
        user_id=user.id,
        jti_hash=hash_jti(jti),
        expires_at=expires_at,
    )
    db.add(rt)
    db.commit()

    return access_token, refresh_token


def rotate_refresh_token(db: Session, raw_refresh_token: str) -> tuple[str, str, User]:
    """
    Validate an existing refresh token, revoke it, and issue a new pair.
    Returns (new_access_token, new_refresh_token, user).
    """
    from jose import JWTError, jwt
    from app.core.security import ALGORITHM, REFRESH_TOKEN_TYPE

    try:
        payload = jwt.decode(raw_refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise UnauthorizedError("Invalid or expired refresh token.")

    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise UnauthorizedError("Token is not a refresh token.")

    jti: str | None = payload.get("jti")
    if not jti:
        raise UnauthorizedError("Refresh token missing JTI.")

    jti_hash = hash_jti(jti)
    stored: RefreshToken | None = db.query(RefreshToken).filter(
        RefreshToken.jti_hash == jti_hash
    ).first()

    if stored is None or stored.is_revoked:
        raise UnauthorizedError("Refresh token has been revoked.")

    now = datetime.now(tz=timezone.utc)
    if stored.expires_at.replace(tzinfo=timezone.utc) < now:
        raise UnauthorizedError("Refresh token has expired.")

    user: User | None = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User account not found or deactivated.")

    stored.is_revoked = True
    db.commit()

    access_token, refresh_token = create_token_pair(db, user)
    return access_token, refresh_token, user


def revoke_refresh_token(db: Session, raw_refresh_token: str) -> None:
    """Revoke a refresh token on logout."""
    from jose import JWTError, jwt
    from app.core.security import ALGORITHM

    try:
        payload = jwt.decode(raw_refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return

    jti: str | None = payload.get("jti")
    if not jti:
        return

    jti_hash = hash_jti(jti)
    stored: RefreshToken | None = db.query(RefreshToken).filter(
        RefreshToken.jti_hash == jti_hash
    ).first()
    if stored and not stored.is_revoked:
        stored.is_revoked = True
        db.commit()


def initiate_password_reset(db: Session, email: str) -> str | None:
    """
    Generate a secure password reset token for the given email.

    Returns the raw token (to be sent via email) or None if email not found.
    We return None and log nothing to prevent email enumeration.
    """
    user: User | None = db.query(User).filter(User.email == email).first()
    if user is None:
        return None

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False,
    ).update({"is_used": True})

    raw_token = generate_secure_token(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=1)

    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(prt)
    db.commit()

    return raw_token


def complete_password_reset(db: Session, raw_token: str, new_password: str) -> None:
    """Validate a reset token and update the password."""
    token_hash = hash_token(raw_token)
    prt: PasswordResetToken | None = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False,
    ).first()

    if prt is None:
        raise BadRequestError("Invalid or expired password reset token.")

    now = datetime.now(tz=timezone.utc)
    if prt.expires_at.replace(tzinfo=timezone.utc) < now:
        prt.is_used = True
        db.commit()
        raise BadRequestError("Password reset token has expired.")

    user: User | None = db.get(User, prt.user_id)
    if user is None:
        raise NotFoundError("User")

    user.hashed_password = hash_password(new_password)
    prt.is_used = True
    db.commit()


def verify_user_email(db: Session, raw_token: str) -> None:
    """Mark user as verified using the email verification token."""
    token_hash = hash_token(raw_token)
    prt: PasswordResetToken | None = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.is_used == False,
    ).first()

    if prt is None:
        raise BadRequestError("Invalid or expired verification token.")

    now = datetime.now(tz=timezone.utc)
    if prt.expires_at.replace(tzinfo=timezone.utc) < now:
        prt.is_used = True
        db.commit()
        raise BadRequestError("Verification token has expired.")

    user: User | None = db.get(User, prt.user_id)
    if user is None:
        raise NotFoundError("User")

    user.is_verified = True
    prt.is_used = True
    db.commit()


def generate_email_verification_token(db: Session, user: User) -> str:
    """Issue an email verification token."""
    raw_token = generate_secure_token(32)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=24)

    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(prt)
    db.commit()
    return raw_token


from app.core.exceptions import ForbiddenError
