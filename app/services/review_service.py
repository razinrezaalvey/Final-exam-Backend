"""Review service."""

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.parcel import DeliveryStatus, Parcel
from app.models.review import Review
from app.models.user import User
from app.schemas.misc import ReviewCreateRequest


def create_review(db: Session, data: ReviewCreateRequest, customer: User) -> Review:
    parcel: Parcel | None = db.get(Parcel, data.parcel_id)
    if parcel is None:
        raise NotFoundError("Parcel")

    if parcel.customer_id != customer.id:
        raise ForbiddenError("You do not own this parcel.")

    if parcel.delivery_status != DeliveryStatus.delivered:
        raise BadRequestError("You can only review delivered parcels.")

    existing = db.query(Review).filter(
        Review.customer_id == customer.id,
        Review.parcel_id == data.parcel_id,
    ).first()
    if existing:
        raise ConflictError("You have already reviewed this parcel.")

    review = Review(
        customer_id=customer.id,
        parcel_id=data.parcel_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(
    db: Session,
    *,
    customer_id: int | None = None,
    parcel_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Review], int]:
    query = db.query(Review)
    if customer_id:
        query = query.filter(Review.customer_id == customer_id)
    if parcel_id:
        query = query.filter(Review.parcel_id == parcel_id)
    total = query.count()
    items = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    return items, total
