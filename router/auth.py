from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

from deps import get_db, hash_password, verify_password
import models

router = APIRouter()

SECRET_KEY = "5b70dc4b0006fdf65224e06aa2edb30c4f00b02ea1e85dc48ee4ea2997edf4ac"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------- Schemas ----------

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: str = "customer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ---------- Helpers ----------

def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, db: Session) -> str:
    token = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(models.RefreshToken(user_id=user_id, token=token, expires_at=expires))
    db.commit()
    return token


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


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


# ---------- Routes ----------

@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    role = body.role if body.role in ("customer", "agent") else "customer"
    user = models.User(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        hashed_password=hash_password(body.password),
        role=role,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == "agent":
        db.add(models.AgentProfile(user_id=user.id))
        db.commit()

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, db)

    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_dict(user),
    }

    return {
        **token_data,
        "success": True,
        "data": token_data,
    }


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    email = None
    password = None

    # Support JSON payload (React Frontend)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass

    # Support Form data (Swagger UI / OAuth2 form)
    if not email or not password:
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, db)

    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_dict(user),
    }

    return {
        **token_data,
        "success": True,
        "data": token_data,
    }


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    token_row = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == body.refresh_token
    ).first()
    if token_row:
        token_row.revoked = True
        db.commit()
    return {"success": True, "message": "Logged out"}


@router.post("/refresh")
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    token_row = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == body.refresh_token,
        models.RefreshToken.revoked == False,
    ).first()
    if not token_row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_row.revoked = True
    db.commit()

    user = db.query(models.User).filter(models.User.id == token_row.user_id).first()
    access_token = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id, db)

    token_data = {
        "access_token": access_token,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }

    return {
        **token_data,
        "success": True,
        "data": token_data,
    }


@router.get("/me")
def me(current_user: models.User = Depends(get_current_user)):
    d = user_dict(current_user)
    return {**d, "success": True, "data": d}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return {"success": True, "message": "Password reset instructions sent if email exists."}
