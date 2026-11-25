"""Agent schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.agent_profile import AvailabilityStatus, VehicleType
from app.schemas.user import UserResponse


class AgentProfileResponse(BaseModel):
    id: int
    user_id: int
    vehicle_type: VehicleType | None
    vehicle_number: str | None
    license_number: str | None
    availability_status: AvailabilityStatus
    total_deliveries: int
    total_earnings: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentWithUserResponse(BaseModel):
    user: UserResponse
    profile: AgentProfileResponse | None

    model_config = {"from_attributes": True}


class AgentProfileUpdateRequest(BaseModel):
    vehicle_type: VehicleType | None = None
    vehicle_number: str | None = Field(default=None, max_length=50)
    license_number: str | None = Field(default=None, max_length=100)
    availability_status: AvailabilityStatus | None = None


class AdminCreateAgentRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)
    vehicle_type: VehicleType | None = None
    vehicle_number: str | None = Field(default=None, max_length=50)
    license_number: str | None = Field(default=None, max_length=100)


class AssignmentResponse(BaseModel):
    id: int
    parcel_id: int
    agent_id: int
    assigned_by: int | None
    assignment_status: str
    note: str | None
    assigned_at: datetime
    responded_at: datetime | None

    model_config = {"from_attributes": True}


class AssignParcelRequest(BaseModel):
    parcel_id: int
    agent_id: int
    note: str | None = Field(default=None, max_length=500)


class RespondAssignmentRequest(BaseModel):
    accept: bool
    note: str | None = Field(default=None, max_length=500)
