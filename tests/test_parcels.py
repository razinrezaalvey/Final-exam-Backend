"""Tests: RBAC, parcel management, agent isolation, payment duplicate prevention."""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    create_customer, create_admin_user, create_agent_user,
    get_auth_headers, login_user
)

PARCEL_PAYLOAD = {
    "sender_name": "Sender",
    "sender_phone": "01700000001",
    "sender_address": "123 Sender Street, Dhaka",
    "receiver_name": "Receiver",
    "receiver_phone": "01800000001",
    "receiver_address": "456 Receiver Ave, Chittagong",
    "pickup_address": "123 Sender Street, Dhaka",
    "delivery_address": "456 Receiver Ave, Chittagong",
    "parcel_type": "small_package",
    "parcel_weight": 1.5,
    "cod_amount": 0,
}


def test_customer_cannot_access_admin_endpoint(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 403


def test_agent_cannot_access_admin_endpoint(client: TestClient, db):
    agent, _ = create_agent_user(db)
    headers = get_auth_headers(client, agent.email, "Agent1234")
    resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 403


def test_admin_can_access_dashboard(client: TestClient, db):
    create_admin_user(db)
    headers = get_auth_headers(client, "admin@swiftcourier.com", "Admin1234")
    resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data


def test_unauthenticated_cannot_access_protected_endpoint(client: TestClient):
    resp = client.get("/api/v1/parcels")
    assert resp.status_code == 401


def test_customer_can_create_parcel(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tracking_number"].startswith("SWC")
    assert data["delivery_status"] == "pending"
    assert data["delivery_charge"] > 0


def test_tracking_number_uniqueness(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    tracking_numbers = set()
    for _ in range(5):
        resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
        assert resp.status_code == 201
        tracking_numbers.add(resp.json()["tracking_number"])
    assert len(tracking_numbers) == 5


def test_agent_cannot_create_parcel(client: TestClient, db):
    agent, _ = create_agent_user(db)
    headers = get_auth_headers(client, agent.email, "Agent1234")
    resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
    assert resp.status_code == 403


def test_customer_data_isolation(client: TestClient):
    """Customer A cannot see Customer B's parcel."""
    create_customer(client, email="customerA@test.com")
    create_customer(client, email="customerB@test.com")

    headers_a = get_auth_headers(client, "customerA@test.com", "Customer1234")
    create_resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers_a)
    parcel_id = create_resp.json()["id"]

    headers_b = get_auth_headers(client, "customerB@test.com", "Customer1234")
    resp = client.get(f"/api/v1/parcels/{parcel_id}", headers=headers_b)
    assert resp.status_code == 403


def test_customer_can_cancel_pending_parcel(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    create_resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
    parcel_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/parcels/{parcel_id}/status",
        json={"new_status": "cancelled"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["delivery_status"] == "cancelled"


def test_customer_cannot_cancel_assigned_parcel(client: TestClient, db):
    create_customer(client)
    admin = create_admin_user(db)
    agent, _ = create_agent_user(db)

    cust_headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    admin_headers = get_auth_headers(client, "admin@swiftcourier.com", "Admin1234")

    create_resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=cust_headers)
    parcel_id = create_resp.json()["id"]

    client.patch(
        f"/api/v1/parcels/{parcel_id}/status",
        json={"new_status": "confirmed"},
        headers=admin_headers,
    )

    client.post(
        "/api/v1/agents/assignments",
        json={"parcel_id": parcel_id, "agent_id": agent.id},
        headers=admin_headers,
    )

    resp = client.patch(
        f"/api/v1/parcels/{parcel_id}/status",
        json={"new_status": "cancelled"},
        headers=cust_headers,
    )
    assert resp.status_code == 400


def test_invalid_status_transition(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    create_resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
    parcel_id = create_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/parcels/{parcel_id}/status",
        json={"new_status": "delivered"},
        headers=headers,
    )
    assert resp.status_code in (400, 403)


def test_public_tracking(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    create_resp = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers)
    tracking_number = create_resp.json()["tracking_number"]

    resp = client.get(f"/api/v1/tracking/{tracking_number}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracking_number"] == tracking_number
    assert data["delivery_status"] == "pending"


def test_tracking_invalid_number(client: TestClient):
    resp = client.get("/api/v1/tracking/SWCINVALIDTRACKING")
    assert resp.status_code == 404


def test_agent_isolation(client: TestClient, db):
    """Agent A cannot update a parcel assigned to Agent B."""
    create_customer(client)
    admin = create_admin_user(db)
    agent_a, _ = create_agent_user(db, email="agent_a@test.com")
    agent_b, _ = create_agent_user(db, email="agent_b@test.com")

    cust_headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    admin_headers = get_auth_headers(client, "admin@swiftcourier.com", "Admin1234")
    agent_b_headers = get_auth_headers(client, "agent_b@test.com", "Agent1234")

    parcel = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=cust_headers).json()
    client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                 json={"new_status": "confirmed"}, headers=admin_headers)
    client.post("/api/v1/agents/assignments",
                json={"parcel_id": parcel["id"], "agent_id": agent_a.id},
                headers=admin_headers)

    resp = client.patch(
        f"/api/v1/parcels/{parcel['id']}/status",
        json={"new_status": "picked_up"},
        headers=agent_b_headers,
    )
    assert resp.status_code == 403


def test_payment_duplicate_prevention(client: TestClient, db):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")

    parcel = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers).json()
    parcel_id = parcel["id"]

    payment_payload = {
        "parcel_id": parcel_id,
        "payment_method": "online",
        "idempotency_key": "unique-key-001",
    }

    resp1 = client.post("/api/v1/payments", json=payment_payload, headers=headers)
    assert resp1.status_code == 201

    payment_payload2 = {
        "parcel_id": parcel_id,
        "payment_method": "online",
        "idempotency_key": "unique-key-002",
    }
    resp2 = client.post("/api/v1/payments", json=payment_payload2, headers=headers)
    assert resp2.status_code == 409


def test_idempotent_payment(client: TestClient, db):
    """Same idempotency key returns the same payment."""
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")

    parcel = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=headers).json()

    payload = {
        "parcel_id": parcel["id"],
        "payment_method": "cash_on_delivery",
        "idempotency_key": "idempotent-key-xyz",
    }

    resp1 = client.post("/api/v1/payments", json=payload, headers=headers)
    resp2 = client.post("/api/v1/payments", json=payload, headers=headers)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]


def test_invalid_parcel_weight(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    payload = {**PARCEL_PAYLOAD, "parcel_weight": -1}
    resp = client.post("/api/v1/parcels", json=payload, headers=headers)
    assert resp.status_code == 422


def test_invalid_review_rating(client: TestClient):
    create_customer(client)
    headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    resp = client.post("/api/v1/reviews", json={
        "parcel_id": 999,
        "rating": 10,
        "comment": "Too high",
    }, headers=headers)
    assert resp.status_code == 422


def test_admin_can_list_all_users(client: TestClient, db):
    create_customer(client)
    create_admin_user(db)
    admin_headers = get_auth_headers(client, "admin@swiftcourier.com", "Admin1234")
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert data["total"] >= 1


def test_parcel_assignment_workflow(client: TestClient, db):
    """Full workflow: create → confirm → assign → agent accepts → pickup → deliver."""
    create_customer(client)
    admin = create_admin_user(db)
    agent, _ = create_agent_user(db)

    cust_headers = get_auth_headers(client, "customer@test.com", "Customer1234")
    admin_headers = get_auth_headers(client, "admin@swiftcourier.com", "Admin1234")
    agent_headers = get_auth_headers(client, agent.email, "Agent1234")

    parcel = client.post("/api/v1/parcels", json=PARCEL_PAYLOAD, headers=cust_headers).json()
    assert parcel["delivery_status"] == "pending"

    r = client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                     json={"new_status": "confirmed"}, headers=admin_headers)
    assert r.status_code == 200

    assign_resp = client.post(
        "/api/v1/agents/assignments",
        json={"parcel_id": parcel["id"], "agent_id": agent.id},
        headers=admin_headers,
    )
    assert assign_resp.status_code == 201
    assignment_id = assign_resp.json()["id"]

    r = client.post(
        f"/api/v1/agents/assignments/{assignment_id}/respond",
        json={"accept": True},
        headers=agent_headers,
    )
    assert r.status_code == 200

    r = client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                     json={"new_status": "picked_up"}, headers=agent_headers)
    assert r.status_code == 200

    r = client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                     json={"new_status": "in_transit"}, headers=agent_headers)
    assert r.status_code == 200

    r = client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                     json={"new_status": "out_for_delivery"}, headers=agent_headers)
    assert r.status_code == 200

    r = client.patch(f"/api/v1/parcels/{parcel['id']}/status",
                     json={"new_status": "delivered"}, headers=agent_headers)
    assert r.status_code == 200
    assert r.json()["delivery_status"] == "delivered"

