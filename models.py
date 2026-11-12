from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="customer")  # customer | agent | admin
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now_utc)

    agent_profile = relationship("AgentProfile", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user")


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    vehicle_type = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    availability_status = Column(String, default="available")  # available | busy | offline
    total_deliveries = Column(Integer, default=0)
    total_earnings = Column(Float, default=0.0)

    user = relationship("User", back_populates="agent_profile")


class Parcel(Base):
    __tablename__ = "parcels"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String, unique=True, index=True, nullable=False)
    sender_name = Column(String, nullable=False)
    sender_phone = Column(String, nullable=False)
    sender_address = Column(String, nullable=False)
    receiver_name = Column(String, nullable=False)
    receiver_phone = Column(String, nullable=False)
    receiver_address = Column(String, nullable=False)
    pickup_address = Column(String, nullable=True)
    delivery_address = Column(String, nullable=True)
    parcel_type = Column(String, nullable=True)
    parcel_weight = Column(Float, nullable=True)
    cod_amount = Column(Float, default=0.0)
    status = Column(String, default="pending")  # pending | picked_up | in_transit | delivered | cancelled
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_utc)

    user = relationship("User", back_populates="refresh_tokens")


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    description = Column(String, nullable=True)

