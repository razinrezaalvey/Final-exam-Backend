"""User service — user management operations."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import AdminCreateUserRequest, AdminUpdateUserRequest, UserUpdateRequest, ChangePasswordRequest


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def update_own_profile(db: Session, user: User, data: UserUpdateRequest) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: ChangePasswordRequest) -> None:
    from app.core.exceptions import BadRequestError
    if not verify_password(data.current_password, user.hashed_password):
        raise BadRequestError("Current password is incorrect.")
    user.hashed_password = hash_password(data.new_password)
    db.commit()


def admin_create_user(db: Session, data: AdminCreateUserRequest) -> User:
    existing = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if existing:
        raise ConflictError("An account with this email already exists.")

    user = User(
        full_name=data.full_name,
        email=data.email.strip().lower(),
        hashed_password=hash_password(data.password),
        phone=data.phone,
        role=data.role,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def admin_update_user(db: Session, user_id: int, data: AdminUpdateUserRequest) -> User:
    user = get_user_by_id(db, user_id)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_verified is not None:
        user.is_verified = data.is_verified
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        search_like = f"%{search}%"
        query = query.filter(
            (User.full_name.ilike(search_like)) | (User.email.ilike(search_like))
        )
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return users, total
