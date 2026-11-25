"""SwiftCourier FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "SwiftCourier — Professional Courier & Logistics Management Platform API. "
        "Provides complete backend for customer parcel management, agent delivery workflows, "
        "and admin control panel."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint — returns application status."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "debug": settings.DEBUG,
    }


@app.get("/", tags=["Root"])
def root():
    """Root redirect info."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }
