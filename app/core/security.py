"""Security utilities — password hashing, JWT creation/verification."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from jose import JWTError, jwt

from app.config import settings


_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches hashed_password."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """Check if the stored hash should be upgraded to current parameters."""
    return _hasher.check_needs_rehash(hashed_password)


ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def create_access_token(subject: int, role: str) -> str:
    """Create a short-lived JWT access token."""
    now = _utc_now()
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(subject),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: int) -> tuple[str, str]:
    """
    Create a refresh token.

    Returns (encoded_token, jti) so the caller can store jti_hash in the DB.
    """
    now = _utc_now()
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(subject),
        "type": REFRESH_TOKEN_TYPE,
        "iat": now,
        "exp": expire,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises JWTError on any failure.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def hash_jti(jti: str) -> str:
    """Produce a SHA-256 hex digest of a JTI string."""
    return hashlib.sha256(jti.encode()).hexdigest()


def hash_token(token: str) -> str:
    """Produce a SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random URL-safe token."""
    return secrets.token_urlsafe(nbytes)
