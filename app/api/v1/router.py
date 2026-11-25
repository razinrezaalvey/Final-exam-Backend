"""API v1 main router — assembles all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.parcels import router as parcels_router
from app.api.v1.endpoints.tracking import router as tracking_router
from app.api.v1.endpoints.agents import router as agents_router
from app.api.v1.endpoints.payments import router as payments_router
from app.api.v1.endpoints.misc import (
    reviews_router,
    notifications_router,
    admin_router,
    settings_router,
    reports_router,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(parcels_router)
api_router.include_router(tracking_router)
api_router.include_router(agents_router)
api_router.include_router(payments_router)
api_router.include_router(reviews_router)
api_router.include_router(notifications_router)
api_router.include_router(admin_router)
api_router.include_router(settings_router)
api_router.include_router(reports_router)

