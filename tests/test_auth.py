"""Tests: Authentication flows."""

import pytest
import time
from fastapi.testclient import TestClient

from tests.conftest import (
    create_customer, create_admin_user, create_agent_user,
    get_auth_headers, login_user
)


def test_register_customer_success(client: TestClient):
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": "Password123",
        "phone": "01700000001",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "john@example.com"
    assert data["role"] == "customer"
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient):
    create_customer(client, email="dup@example.com")
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Duplicate",
        "email": "dup@example.com",
        "password": "Password123",
    })
    assert resp.status_code == 409
    assert "already exists" in resp.json()["error"]["message"]


def test_register_weak_password(client: TestClient):
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Weak",
        "email": "weak@example.com",
        "password": "pass",
    })
    assert resp.status_code == 422


def test_login_success(client: TestClient):
    create_customer(client, email="login@test.com", password="Login1234")
    resp = client.post("/api/v1/auth/login", json={
        "email": "login@test.com",
        "password": "Login1234",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["role"] == "customer"


def test_login_wrong_password(client: TestClient):
    create_customer(client, email="user@test.com")
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "WrongPassword1",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={
        "email": "ghost@test.com",
        "password": "SomePass1",
    })
    assert resp.status_code == 401


def test_get_me_with_valid_token(client: TestClient):
    create_customer(client, email="me@test.com")
    headers = get_auth_headers(client, "me@test.com", "Customer1234")
    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.com"


def test_get_me_without_token(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_get_me_with_invalid_token(client: TestClient):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401


def test_refresh_token_rotation(client: TestClient):
    create_customer(client, email="refresh@test.com")
    login_data = login_user(client, "refresh@test.com", "Customer1234")
    old_refresh = login_data["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_data = resp.json()["data"]
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    assert new_data["refresh_token"] != old_refresh


def test_revoked_refresh_token_rejected(client: TestClient):
    create_customer(client, email="revoke@test.com")
    login_data = login_user(client, "revoke@test.com", "Customer1234")
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


def test_public_registration_always_creates_customer(client: TestClient):
    """Security: public registration cannot create admin or agent accounts."""
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Hacker",
        "email": "hacker@test.com",
        "password": "Hacker1234",
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "customer"


def test_forgot_password_returns_200_regardless(client: TestClient):
    """Prevent email enumeration — always return 200."""
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@test.com"})
    assert resp.status_code == 200


def test_reset_password_flow(client: TestClient, db):
    from app.models.user import User
    create_customer(client, email="reset@test.com")

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "reset@test.com"})
    assert resp.status_code == 200

    from app.models.password_reset_token import PasswordResetToken
    user = db.query(User).filter(User.email == "reset@test.com").first()
    token_record = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False,
    ).first()
    assert token_record is not None

    from app.services.auth_service import initiate_password_reset, complete_password_reset
    raw_token = initiate_password_reset(db, "reset@test.com")
    assert raw_token is not None

    complete_password_reset(db, raw_token, "NewPassword1")

    resp = client.post("/api/v1/auth/login", json={
        "email": "reset@test.com",
        "password": "NewPassword1",
    })
    assert resp.status_code == 200

