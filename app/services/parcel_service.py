"""Parcel service — core parcel management business logic."""

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError, ConflictError
from app.models.parcel import VALID_STATUS_TRANSITIONS, DeliveryStatus, Parcel
from app.models.parcel_status_history import ParcelStatusHistory
from app.models.user import User, UserRole
from app.schemas.parcel import ParcelCreateRequest, ParcelStatusUpdateRequest, ParcelUpdateRequest
from app.utils.pricing import calculate_delivery_charge
from app.utils.tracking import generate_tracking_number


CUSTOMER_CANCELLABLE_STATUSES = {
    DeliveryStatus.pending,
    DeliveryStatus.confirmed,
}


def create_parcel(db: Session, data: ParcelCreateRequest, customer: User) -> Parcel:
    """Create a new parcel — delivery charge is always calculated server-side."""
    charge = calculate_delivery_charge(
        db, weight_kg=data.parcel_weight, cod_amount=data.cod_amount
    )

    attempts = 0
    tracking_number = generate_tracking_number()
    while db.query(Parcel).filter(Parcel.tracking_number == tracking_number).first():
        tracking_number = generate_tracking_number()
        attempts += 1
        if attempts > 10:
            raise BadRequestError("Failed to generate unique tracking number. Try again.")

    parcel = Parcel(
        tracking_number=tracking_number,
        customer_id=customer.id,
        sender_name=data.sender_name,
        sender_phone=data.sender_phone,
        sender_address=data.sender_address,
        receiver_name=data.receiver_name,
        receiver_phone=data.receiver_phone,
        receiver_address=data.receiver_address,
        pickup_address=data.pickup_address,
        delivery_address=data.delivery_address,
        parcel_type=data.parcel_type,
        parcel_weight=data.parcel_weight,
        parcel_description=data.parcel_description,
        special_instruction=data.special_instruction,
        delivery_charge=charge,
        cod_amount=data.cod_amount,
    )
    db.add(parcel)
    db.flush()

    _record_status_change(db, parcel=parcel, old_status=None, new_status=DeliveryStatus.pending, updated_by=customer.id)

    db.commit()
    db.refresh(parcel)
    return parcel


def get_parcel_by_id(db: Session, parcel_id: int) -> Parcel:
    parcel = db.get(Parcel, parcel_id)
    if parcel is None:
        raise NotFoundError("Parcel")
    return parcel


def get_parcel_by_tracking(db: Session, tracking_number: str) -> Parcel:
    parcel = db.query(Parcel).filter(
        Parcel.tracking_number == tracking_number.upper()
    ).first()
    if parcel is None:
        raise NotFoundError("Parcel")
    return parcel


def list_parcels(
    db: Session,
    *,
    customer_id: int | None = None,
    agent_id: int | None = None,
    status: DeliveryStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Parcel], int]:
    query = db.query(Parcel)
    if customer_id is not None:
        query = query.filter(Parcel.customer_id == customer_id)
    if agent_id is not None:
        query = query.filter(Parcel.agent_id == agent_id)
    if status is not None:
        query = query.filter(Parcel.delivery_status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (Parcel.tracking_number.ilike(like))
            | (Parcel.receiver_name.ilike(like))
            | (Parcel.sender_name.ilike(like))
        )
    total = query.count()
    parcels = query.order_by(Parcel.created_at.desc()).offset(skip).limit(limit).all()
    return parcels, total


def update_parcel_status(
    db: Session,
    parcel: Parcel,
    data: ParcelStatusUpdateRequest,
    acting_user: User,
) -> Parcel:
    """
    Perform a status transition with full validation.

    Rules:
    - Validate transition is allowed.
    - Agent can only update their own assigned parcel.
    - Customer can only cancel eligible parcels.
    - Admin can perform admin-authorized transitions.
    """
    old_status = parcel.delivery_status
    new_status = data.new_status

    if old_status == new_status:
        raise BadRequestError("Parcel is already in this status.")

    allowed = VALID_STATUS_TRANSITIONS.get(old_status, [])
    if new_status not in allowed:
        raise BadRequestError(
            f"Cannot transition from '{old_status}' to '{new_status}'. "
            f"Allowed: {[s.value for s in allowed]}"
        )

    if acting_user.role == UserRole.customer:
        if new_status != DeliveryStatus.cancelled:
            raise ForbiddenError("Customers can only cancel parcels.")
        if old_status not in CUSTOMER_CANCELLABLE_STATUSES:
            raise BadRequestError(
                f"You can only cancel parcels in 'pending' or 'confirmed' status. "
                f"Current status: {old_status}"
            )
        if parcel.customer_id != acting_user.id:
            raise ForbiddenError("You do not own this parcel.")

    elif acting_user.role == UserRole.agent:
        if parcel.agent_id != acting_user.id:
            raise ForbiddenError("This parcel is not assigned to you.")
        agent_allowed_transitions = {
            DeliveryStatus.assigned: [DeliveryStatus.picked_up],
            DeliveryStatus.picked_up: [DeliveryStatus.in_transit],
            DeliveryStatus.in_transit: [DeliveryStatus.out_for_delivery],
            DeliveryStatus.out_for_delivery: [DeliveryStatus.delivered, DeliveryStatus.failed],
        }
        agent_allowed = agent_allowed_transitions.get(old_status, [])
        if new_status not in agent_allowed:
            raise ForbiddenError(
                f"Agent cannot perform this transition: {old_status} -> {new_status}"
            )

    elif acting_user.role == UserRole.admin:
        pass

    parcel.delivery_status = new_status
    _record_status_change(
        db, parcel=parcel, old_status=old_status, new_status=new_status,
        updated_by=acting_user.id, note=data.note
    )

    if new_status == DeliveryStatus.delivered and parcel.agent_id:
        from app.models.agent_profile import AgentProfile
        profile = db.query(AgentProfile).filter(
            AgentProfile.user_id == parcel.agent_id
        ).first()
        if profile:
            commission_pct = 10.0
            profile.total_deliveries += 1
            profile.total_earnings = float(profile.total_earnings) + round(
                float(parcel.delivery_charge) * commission_pct / 100, 2
            )

    db.commit()
    db.refresh(parcel)
    return parcel


def admin_update_parcel(db: Session, parcel: Parcel, data: ParcelUpdateRequest) -> Parcel:
    """Admin can update parcel details before pickup."""
    if parcel.delivery_status not in (
        DeliveryStatus.pending, DeliveryStatus.confirmed
    ):
        raise BadRequestError("Parcel details can only be edited before it is picked up.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(parcel, field, value)

    db.commit()
    db.refresh(parcel)
    return parcel


def _record_status_change(
    db: Session,
    *,
    parcel: Parcel,
    old_status: DeliveryStatus | None,
    new_status: DeliveryStatus,
    updated_by: int | None = None,
    note: str | None = None,
) -> None:
    history = ParcelStatusHistory(
        parcel_id=parcel.id,
        updated_by=updated_by,
        old_status=old_status.value if old_status else None,
        new_status=new_status.value,
        note=note,
    )
    db.add(history)
