"""Agent management endpoints."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_current_active_user, require_admin, require_agent, get_client_ip
)
from app.models.agent_assignment import AssignmentStatus
from app.models.user import User
from app.schemas.agent import (
    AdminCreateAgentRequest, AgentProfileResponse, AgentProfileUpdateRequest,
    AssignmentResponse, AssignParcelRequest, RespondAssignmentRequest,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.user import UserResponse
from app.services import agent_service
from app.utils.audit import log_action
from app.utils.notifications import create_notification
from app.models.notification import NotificationType

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_agent(
    data: AdminCreateAgentRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: create a new delivery agent with profile."""
    user = agent_service.create_agent(db, data)
    log_action(
        db,
        user_id=admin.id,
        action="admin.create_agent",
        resource_type="User",
        resource_id=user.id,
        ip_address=get_client_ip(request),
    )
    db.commit()
    return user


@router.get("/me/profile", response_model=AgentProfileResponse)
def get_my_agent_profile(
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """Agent: get own profile."""
    return agent_service.get_agent_profile(db, agent.id)


@router.put("/me/profile", response_model=AgentProfileResponse)
def update_my_agent_profile(
    data: AgentProfileUpdateRequest,
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """Agent: update own profile."""
    return agent_service.update_agent_profile(db, agent.id, data)


@router.get("/me/assignments", response_model=PaginatedResponse[AssignmentResponse])
def list_my_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: AssignmentStatus | None = Query(default=None, alias="status"),
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """Agent: list own assignments."""
    skip = (page - 1) * page_size
    items, total = agent_service.list_agent_assignments(
        db, agent_id=agent.id, status=status_filter, skip=skip, limit=page_size
    )
    return PaginatedResponse.build(
        data=[AssignmentResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/assignments/{assignment_id}/respond", response_model=AssignmentResponse)
def respond_to_assignment(
    assignment_id: int,
    data: RespondAssignmentRequest,
    request: Request,
    agent: User = Depends(require_agent),
    db: Session = Depends(get_db),
):
    """Agent: accept or reject a parcel assignment."""
    assignment = agent_service.respond_to_assignment(db, assignment_id, data, agent)
    log_action(
        db,
        user_id=agent.id,
        action="agent.respond_assignment",
        resource_type="AgentAssignment",
        resource_id=assignment_id,
        details=f"{'Accepted' if data.accept else 'Rejected'} assignment",
        ip_address=get_client_ip(request),
    )
    db.commit()
    return assignment


@router.get("/{agent_id}/profile", response_model=AgentProfileResponse)
def admin_get_agent_profile(
    agent_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: get agent profile by user ID."""
    return agent_service.get_agent_profile(db, agent_id)


@router.post("/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_parcel(
    data: AssignParcelRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: assign a parcel to a delivery agent."""
    assignment = agent_service.assign_parcel_to_agent(
        db, data.parcel_id, data, admin
    )
    log_action(
        db,
        user_id=admin.id,
        action="admin.assign_parcel",
        resource_type="AgentAssignment",
        resource_id=assignment.id,
        details=f"Assigned parcel #{data.parcel_id} to agent #{data.agent_id}",
        ip_address=get_client_ip(request),
    )
    create_notification(
        db,
        user_id=data.agent_id,
        title="New Delivery Assignment",
        message=f"You have been assigned a new delivery task. Assignment #{assignment.id}.",
        notification_type=NotificationType.assignment,
    )
    db.commit()
    return assignment


@router.get("/assignments", response_model=PaginatedResponse[AssignmentResponse])
def list_all_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    agent_id: int | None = Query(default=None),
    parcel_id: int | None = Query(default=None),
    status_filter: AssignmentStatus | None = Query(default=None, alias="status"),
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin: list all assignments."""
    skip = (page - 1) * page_size
    items, total = agent_service.list_agent_assignments(
        db,
        agent_id=agent_id,
        parcel_id=parcel_id,
        status=status_filter,
        skip=skip,
        limit=page_size,
    )
    return PaginatedResponse.build(
        data=[AssignmentResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )

