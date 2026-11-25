"""Agent service — agent management and assignment operations."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.agent_assignment import AgentAssignment, AssignmentStatus
from app.models.agent_profile import AgentProfile
from app.models.parcel import DeliveryStatus, Parcel
from app.models.parcel_status_history import ParcelStatusHistory
from app.models.user import User, UserRole
from app.schemas.agent import (
    AdminCreateAgentRequest,
    AgentProfileUpdateRequest,
    AssignParcelRequest,
    RespondAssignmentRequest,
)


def create_agent(db: Session, data: AdminCreateAgentRequest) -> User:
    """Admin creates a new agent with profile."""
    from app.services.user_service import get_user_by_email
    existing = get_user_by_email(db, data.email.strip().lower())
    if existing:
        raise ConflictError("An account with this email already exists.")

    user = User(
        full_name=data.full_name,
        email=data.email.strip().lower(),
        hashed_password=hash_password(data.password),
        phone=data.phone,
        role=UserRole.agent,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()

    profile = AgentProfile(
        user_id=user.id,
        vehicle_type=data.vehicle_type,
        vehicle_number=data.vehicle_number,
        license_number=data.license_number,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user


def get_agent_profile(db: Session, user_id: int) -> AgentProfile:
    profile = db.query(AgentProfile).filter(AgentProfile.user_id == user_id).first()
    if profile is None:
        raise NotFoundError("Agent profile")
    return profile


def update_agent_profile(
    db: Session, user_id: int, data: AgentProfileUpdateRequest
) -> AgentProfile:
    profile = get_agent_profile(db, user_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


def assign_parcel_to_agent(
    db: Session, parcel_id: int, data: AssignParcelRequest, assigned_by: User
) -> AgentAssignment:
    """Admin assigns a parcel to an agent."""
    parcel: Parcel | None = db.get(Parcel, parcel_id)
    if parcel is None:
        raise NotFoundError("Parcel")

    if parcel.delivery_status != DeliveryStatus.confirmed:
        raise BadRequestError(
            f"Parcel must be in 'confirmed' status to assign. Current: {parcel.delivery_status}"
        )

    agent_user: User | None = db.get(User, data.agent_id)
    if agent_user is None or agent_user.role != UserRole.agent:
        raise NotFoundError("Agent")

    if not agent_user.is_active:
        raise BadRequestError("Agent account is deactivated.")

    existing = db.query(AgentAssignment).filter(
        AgentAssignment.parcel_id == parcel_id,
        AgentAssignment.assignment_status == AssignmentStatus.pending,
    ).first()
    if existing:
        raise ConflictError("Parcel already has a pending assignment.")


    if assigned_by.role == UserRole.agent and assigned_by.id == data.agent_id:
        raise ForbiddenError("Agents cannot assign parcels to themselves.")

    assignment = AgentAssignment(
        parcel_id=parcel_id,
        agent_id=data.agent_id,
        assigned_by=assigned_by.id,
        note=data.note,
    )
    db.add(assignment)

    parcel.delivery_status = DeliveryStatus.assigned
    parcel.agent_id = data.agent_id

    history = ParcelStatusHistory(
        parcel_id=parcel_id,
        updated_by=assigned_by.id,
        old_status=DeliveryStatus.confirmed.value,
        new_status=DeliveryStatus.assigned.value,
        note=f"Assigned to agent #{data.agent_id}",
    )
    db.add(history)
    db.commit()
    db.refresh(assignment)
    return assignment


def respond_to_assignment(
    db: Session, assignment_id: int, data: RespondAssignmentRequest, agent: User
) -> AgentAssignment:
    """Agent accepts or rejects an assignment."""
    assignment: AgentAssignment | None = db.get(AgentAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Assignment")

    if assignment.agent_id != agent.id:
        raise ForbiddenError("This assignment is not yours.")

    if assignment.assignment_status != AssignmentStatus.pending:
        raise BadRequestError("Assignment has already been responded to.")

    assignment.assignment_status = (
        AssignmentStatus.accepted if data.accept else AssignmentStatus.rejected
    )
    assignment.responded_at = datetime.now(tz=timezone.utc)
    if data.note:
        assignment.note = data.note

    if not data.accept:
        parcel: Parcel | None = db.get(Parcel, assignment.parcel_id)
        if parcel:
            parcel.delivery_status = DeliveryStatus.confirmed
            parcel.agent_id = None
            history = ParcelStatusHistory(
                parcel_id=parcel.id,
                updated_by=agent.id,
                old_status=DeliveryStatus.assigned.value,
                new_status=DeliveryStatus.confirmed.value,
                note="Agent rejected assignment",
            )
            db.add(history)

    db.commit()
    db.refresh(assignment)
    return assignment


def list_agent_assignments(
    db: Session,
    *,
    agent_id: int | None = None,
    parcel_id: int | None = None,
    status: AssignmentStatus | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[AgentAssignment], int]:
    query = db.query(AgentAssignment)
    if agent_id:
        query = query.filter(AgentAssignment.agent_id == agent_id)
    if parcel_id:
        query = query.filter(AgentAssignment.parcel_id == parcel_id)
    if status:
        query = query.filter(AgentAssignment.assignment_status == status)
    total = query.count()
    items = query.order_by(AgentAssignment.assigned_at.desc()).offset(skip).limit(limit).all()
    return items, total
