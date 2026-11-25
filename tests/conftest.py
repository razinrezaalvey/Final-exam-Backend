"""Pytest configuration and shared fixtures for SwiftCourier tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_swiftcourier.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(setup_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db(setup_db):
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_customer(client: TestClient, email="customer@test.com", password="Customer1234") -> dict:
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Test Customer",
        "email": email,
        "password": password,
        "phone": "01700000001",
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


def login_user(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def get_auth_headers(client: TestClient, email: str, password: str) -> dict:
    data = login_user(client, email, password)
    return {"Authorization": f"Bearer {data['access_token']}"}


def create_admin_user(db) -> dict:
    """Create an admin directly in DB (bypasses public registration)."""
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    user = User(
        full_name="Admin User",
        email="admin@swiftcourier.com",
        hashed_password=hash_password("Admin1234"),
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_agent_user(db, email="agent@test.com") -> tuple:
    """Create an agent directly in DB."""
    from app.models.user import User, UserRole
    from app.models.agent_profile import AgentProfile
    from app.core.security import hash_password
    user = User(
        full_name="Test Agent",
        email=email,
        hashed_password=hash_password("Agent1234"),
        role=UserRole.agent,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    profile = AgentProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(user)
    return user, profile

