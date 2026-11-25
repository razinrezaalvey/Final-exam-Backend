# SwiftCourier — Professional Courier & Logistics Management Backend

A production-ready, secure, scalable REST API built with **FastAPI**, **SQLAlchemy ORM 2.0**, **Pydantic v2**, and **Alembic**. Designed to seamlessly pair with modern frontend clients (React/Vite).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Folder Structure](#folder-structure)
5. [Prerequisites & Installation (Windows)](#prerequisites--installation-windows)
6. [Environment Configuration](#environment-configuration)
7. [Database Setup & Migrations](#database-setup--migrations)
   - [Local Development (SQLite)](#local-development-sqlite)
   - [Production (Supabase PostgreSQL)](#production-supabase-postgresql)
   - [Alembic Migration Commands](#alembic-migration-commands)
   - [Database Seeding](#database-seeding)
8. [Running the Application](#running-the-application)
9. [Running Automated Tests](#running-automated-tests)
10. [API Architecture & Endpoints](#api-architecture--endpoints)
11. [Authentication & Security Architecture](#authentication--security-architecture)
12. [Example API Requests & Responses](#example-api-requests--responses)
13. [Frontend (React) Integration Guide](#frontend-react-integration-guide)
14. [Production Deployment Checklist](#production-deployment-checklist)

---

## 1. Project Overview

**SwiftCourier** is an end-to-end logistics platform that powers courier operations across three primary stakeholder roles:
- **Customers**: Request parcel deliveries, track parcels in real time, view order history, cancel eligible requests, and submit ratings/feedback.
- **Delivery Agents**: View assigned delivery tasks, accept or reject assignments, transition delivery states (pickup, in-transit, out for delivery, delivered/failed), and track earnings.
- **Administrators**: Control panel to oversee all parcels, assign parcels to delivery agents, configure platform pricing rules, manage customer and agent accounts, audit logs, and view operational analytics.

---

## 2. Key Features

- **Strict Role-Based Access Control (RBAC)**: Role validation across Customer, Delivery Agent, and Admin roles.
- **Privilege Escalation Prevention**: Public registration is strictly locked to Customer accounts. Agents and Admins can only be created by authenticated Admins.
- **State Machine for Parcels**: Enforced parcel delivery lifecycle (`pending` → `confirmed` → `assigned` → `picked_up` → `in_transit` → `out_for_delivery` → `delivered` / `failed` → `returned`). Arbitrary state skipping is blocked.
- **Audit Logging & Status History**: Every status transition generates an immutable `ParcelStatusHistory` row and records actor IP address and details in `AuditLog`.
- **Server-Side Pricing Engine**: Dynamic calculation based on base delivery charge, per-kg weight tiers, cash-on-delivery (COD) percentage fees, and delivery zones.
- **Argon2id Password Hashing**: State-of-the-art password security with automatic rehashing if parameters are updated.
- **JWT Authentication with Refresh Token Rotation**: Short-lived access tokens (15 mins) and one-time-use refresh tokens stored as SHA-256 hashes in the database with revocation support on logout.
- **Idempotent Payment Handling**: Safe payment architecture supporting Cash on Delivery and online mock gateways with duplicate payment prevention.
- **Complete Test Suite**: Automated Pytest suite covering authentication, RBAC, customer data isolation, agent task isolation, state transitions, idempotency, and input validation.

---

## 3. Technology Stack

- **Python 3.12+ / 3.14**
- **FastAPI**: Modern, high-performance web framework for APIs.
- **SQLAlchemy 2.0**: Declarative ORM mapping with type safety.
- **Pydantic v2 & Pydantic-Settings**: Schema validation and environment parsing.
- **Alembic**: Database migration tool.
- **Argon2-cffi**: Secure password hashing.
- **python-jose[cryptography]**: JWT generation and validation.
- **SQLite**: Zero-configuration database for local development.
- **psycopg (v3)**: Modern PostgreSQL driver for Supabase production database.
- **Pytest & HTTPX**: Automated testing suite.
- **Uvicorn**: Lightning-fast ASGI server.

---

## 4. Folder Structure

```
SwiftCourier-Backend/
│
├── alembic/                       # Alembic migration environment
│   ├── versions/                  # Migration revision files
│   │   └── 4eb6a2f5be24_initial_schema.py
│   ├── env.py                     # Alembic migration runner configuration
│   └── script.py.mako
│
├── app/
│   ├── main.py                    # FastAPI app initialization, middleware, routes
│   ├── config.py                  # Pydantic Settings & environment variables
│   ├── database.py                # Database engine, sessionmaker, and Base model
│   ├── dependencies.py            # FastAPI dependencies (auth, roles, IP tracking)
│   │
│   ├── core/                      # Core infrastructure
│   │   ├── security.py            # Argon2 hashing & JWT utilities
│   │   ├── permissions.py         # Role assertion helpers
│   │   └── exceptions.py          # Custom exception classes & global handlers
│   │
│   ├── models/                    # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py                # User model & UserRole enum
│   │   ├── agent_profile.py       # AgentProfile & VehicleType enum
│   │   ├── parcel.py              # Parcel & DeliveryStatus enum
│   │   ├── parcel_status_history.py
│   │   ├── agent_assignment.py    # AgentAssignment & AssignmentStatus enum
│   │   ├── payment.py             # Payment & PaymentMethod enum
│   │   ├── review.py              # Parcel reviews
│   │   ├── notification.py        # System notifications
│   │   ├── audit_log.py           # Administrative audit trails
│   │   ├── platform_setting.py    # Configurable platform pricing & settings
│   │   ├── refresh_token.py       # Stored refresh token hashes for rotation
│   │   └── password_reset_token.py# Secure password reset tokens
│   │
│   ├── schemas/                   # Pydantic validation schemas
│   │   ├── __init__.py
│   │   ├── common.py              # Pagination & generic response models
│   │   ├── auth.py                # Auth requests & tokens
│   │   ├── user.py                # User registration & profile schemas
│   │   ├── parcel.py              # Parcel CRUD & tracking schemas
│   │   ├── agent.py               # Agent profile & assignment schemas
│   │   └── misc.py                # Payment, Review, Notification, Settings schemas
│   │
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── parcel_service.py
│   │   ├── agent_service.py
│   │   ├── payment_service.py
│   │   ├── review_service.py
│   │   └── admin_service.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py          # Unified v1 router
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── parcels.py
│   │           ├── tracking.py
│   │           ├── agents.py
│   │           ├── payments.py
│   │           └── misc.py        # reviews, notifications, admin, settings, reports
│   │
│   └── utils/
│       ├── tracking.py            # Tracking number generation
│       ├── pricing.py             # Server-side delivery charge calculator
│       ├── audit.py               # Audit log helper
│       └── notifications.py       # Notification dispatch helper
│
├── scripts/
│   └── seed_db.py                 # Initial database seeder (admin & default settings)
│
├── tests/                         # Pytest automated test suite
│   ├── __init__.py
│   ├── conftest.py                # Test client & isolated DB fixtures
│   ├── test_auth.py               # Auth & security tests
│   └── test_parcels.py            # RBAC, parcels, agents, payments tests
│
├── .env                           # Local environment configuration
├── .env.example                   # Environment variable template
├── .gitignore
├── alembic.ini                    # Alembic configuration
├── pyproject.toml                 # Pytest & project metadata
└── requirements.txt               # Python package dependencies
```

---

## 5. Prerequisites & Installation (Windows)

### 1. Prerequisites
- Python 3.12 or newer installed on Windows.
- PowerShell or Windows Terminal.

### 2. Create Virtual Environment
Navigate to the backend directory:
```powershell
cd "d:\Full Stack Project\Final Exam\SwiftCourier-Backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 6. Environment Configuration

Copy the example environment file:
```powershell
Copy-Item .env.example .env
```

Open `.env` and verify the settings:
```ini
APP_NAME="SwiftCourier API"
DEBUG=True

# SQLite local development database
DATABASE_URL=sqlite:///./swiftcourier.db

# Cryptographically strong secret key (minimum 32 characters)
SECRET_KEY=MZpl7VmgK_auCSr3lMKddug2F7UBa3B49og7r4m9eOWNTUIJ_e7f4gepfnC3I7mq

# Token Expirations
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS allowed frontend origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> **Generating a new `SECRET_KEY`**:
> ```powershell
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

---

## 7. Database Setup & Migrations

The database connection is configured strictly via the `DATABASE_URL` environment variable. The application seamlessly supports SQLite and Supabase PostgreSQL with zero code changes.

### Local Development (SQLite)
Default setting in `.env`:
```ini
DATABASE_URL=sqlite:///./swiftcourier.db
```

### Production (Supabase PostgreSQL)
In Supabase, find your database connection details under **Project Settings > Database > Connection String** (URI mode, using Transaction or Session pooler):
```ini
DATABASE_URL=postgresql+psycopg://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```
*Note: We use the modern `psycopg` (v3) binary driver for optimal performance.*

### Alembic Migration Commands

1. **Check current migration status**:
   ```powershell
   python -m alembic current
   ```

2. **Generate a new migration (after modifying models)**:
   ```powershell
   python -m alembic revision --autogenerate -m "describe_changes"
   ```

3. **Apply all pending migrations**:
   ```powershell
   python -m alembic upgrade head
   ```

4. **Roll back the last migration**:
   ```powershell
   python -m alembic downgrade -1
   ```

5. **Verify models match schema without uncommitted drift**:
   ```powershell
   python -m alembic check
   ```

### Database Seeding
To populate default pricing parameters and create the initial administrator account:
```powershell
python scripts/seed_db.py
```
Default Administrator credentials created:
- **Email**: `admin@swiftcourier.com`
- **Password**: `Admin12345`

---

## 8. Running the Application

Start the FastAPI application using Uvicorn:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running:
- **API Base URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
- **Health Check**: `http://127.0.0.1:8000/health`

---

## 9. Running Automated Tests

The test suite runs against an isolated SQLite test database and completely tests RBAC, auth, isolation, transitions, and payments.

Run all tests:
```powershell
python -m pytest tests/ -v
```

Run specific test modules:
```powershell
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_parcels.py -v
```

---

## 10. API Architecture & Endpoints

All application routes are prefixed with `/api/v1/`.

| Group | Method | Endpoint | Access | Description |
|---|---|---|---|---|
| **Auth** | POST | `/api/v1/auth/register` | Public | Register customer account |
| **Auth** | POST | `/api/v1/auth/login` | Public | Authenticate user & get token pair |
| **Auth** | POST | `/api/v1/auth/refresh` | Public | Rotate refresh token |
| **Auth** | POST | `/api/v1/auth/logout` | Authenticated | Revoke refresh token |
| **Auth** | GET | `/api/v1/auth/me` | Authenticated | Get current authenticated user |
| **Auth** | POST | `/api/v1/auth/forgot-password` | Public | Initiate password reset |
| **Auth** | POST | `/api/v1/auth/reset-password` | Public | Complete password reset |
| **Auth** | POST | `/api/v1/auth/verify-email` | Public | Verify user email address |
| **Users** | GET | `/api/v1/users/me` | Authenticated | Get profile details |
| **Users** | PUT | `/api/v1/users/me` | Authenticated | Update full name, phone |
| **Users** | POST | `/api/v1/users/me/change-password` | Authenticated | Change account password |
| **Users** | GET | `/api/v1/users` | Admin | List users (paginated, filtered) |
| **Users** | POST | `/api/v1/users` | Admin | Create agent or admin account |
| **Users** | GET | `/api/v1/users/{id}` | Admin | View user details |
| **Users** | PUT | `/api/v1/users/{id}` | Admin | Activate/deactivate/update user |
| **Parcels** | POST | `/api/v1/parcels` | Customer | Create delivery request |
| **Parcels** | GET | `/api/v1/parcels` | Authenticated | List parcels (role-scoped) |
| **Parcels** | GET | `/api/v1/parcels/{id}` | Authenticated | Get parcel (enforces ownership) |
| **Parcels** | GET | `/api/v1/parcels/{id}/history` | Authenticated | Get status timeline |
| **Parcels** | PATCH| `/api/v1/parcels/{id}/status` | Authenticated | Transition status (RBAC validated) |
| **Parcels** | PUT | `/api/v1/parcels/{id}` | Admin | Edit parcel (before pickup) |
| **Tracking**| GET | `/api/v1/tracking/{tracking_number}` | Public | Public tracking timeline |
| **Agents** | POST | `/api/v1/agents` | Admin | Register agent with vehicle profile |
| **Agents** | GET | `/api/v1/agents/me/profile` | Agent | View own delivery profile |
| **Agents** | PUT | `/api/v1/agents/me/profile` | Agent | Update vehicle / availability |
| **Agents** | GET | `/api/v1/agents/me/assignments` | Agent | View assigned tasks |
| **Agents** | POST | `/api/v1/agents/assignments/{id}/respond` | Agent | Accept or reject assignment |
| **Agents** | POST | `/api/v1/agents/assignments` | Admin | Assign parcel to delivery agent |
| **Agents** | GET | `/api/v1/agents/assignments` | Admin | List all assignments |
| **Agents** | GET | `/api/v1/agents/{id}/profile` | Admin | View agent profile |
| **Payments**| POST | `/api/v1/payments` | Customer | Pay parcel (COD or online) |
| **Payments**| GET | `/api/v1/payments/me` | Customer | Customer payment history |
| **Payments**| GET | `/api/v1/payments` | Admin | List all payments |
| **Reviews** | POST | `/api/v1/reviews` | Customer | Review delivered parcel |
| **Reviews** | GET | `/api/v1/reviews` | Authenticated | List reviews |
| **Notifs** | GET | `/api/v1/notifications` | Authenticated | User notifications |
| **Notifs** | PATCH| `/api/v1/notifications/{id}/read`| Authenticated | Mark notification as read |
| **Admin** | GET | `/api/v1/admin/dashboard` | Admin | Dashboard operational stats |
| **Admin** | GET | `/api/v1/admin/audit-logs` | Admin | Audit trail logs |
| **Settings**| GET | `/api/v1/settings` | Admin | View platform settings |
| **Settings**| GET | `/api/v1/settings/{key}` | Admin | View individual setting |
| **Settings**| PUT | `/api/v1/settings/{key}` | Admin | Update pricing or setting |
| **Reports** | GET | `/api/v1/reports/summary` | Admin | Summary & status breakdown |

---

## 11. Authentication & Security Architecture

### 1. Password Hashing (Argon2id)
- Passwords are encrypted with `Argon2id` (RFC 9106 recommended).
- Password strength requires minimum 8 characters, uppercase, lowercase, and numeric digits.

### 2. JWT Access & Refresh Token Rotation
- Access tokens expire in 15 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- Refresh tokens expire in 7 days (`REFRESH_TOKEN_EXPIRE_DAYS`).
- When a refresh token is presented, the server validates its cryptographic signature, checks that its SHA-256 JTI hash exists in the database and is not revoked, revokes that token, and issues a brand-new token pair.
- On logout (`/api/v1/auth/logout`), the refresh token is immediately revoked.

### 3. Protection Against Privilege Escalation
- The public registration endpoint (`/api/v1/auth/register`) hardcodes the user role to `customer`.
- Agent creation requires admin privileges (`POST /api/v1/agents`).
- Admin user creation requires admin privileges (`POST /api/v1/users`).

### 4. Data Isolation (Multi-Tenancy)
- Customers querying `/api/v1/parcels` only receive parcels where `customer_id == current_user.id`.
- Delivery agents only see parcels where `agent_id == current_user.id`.
- Direct retrieval of parcels (`/api/v1/parcels/{id}`) verifies ownership; unauthorized access yields HTTP 403 Forbidden.

---

## 12. Example API Requests & Responses

### 1. Customer Registration
`POST /api/v1/auth/register`
```json
{
  "full_name": "Rahim Ahmed",
  "email": "rahim@example.com",
  "password": "Password123",
  "phone": "01711223344"
}
```
Response (`201 Created`):
```json
{
  "id": 2,
  "full_name": "Rahim Ahmed",
  "email": "rahim@example.com",
  "phone": "01711223344",
  "role": "customer",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-11-03T14:48:40Z",
  "updated_at": "2026-11-03T14:48:40Z"
}
```

### 2. User Login
`POST /api/v1/auth/login`
```json
{
  "email": "rahim@example.com",
  "password": "Password123"
}
```
Response (`200 OK`):
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": 2,
      "full_name": "Rahim Ahmed",
      "email": "rahim@example.com",
      "role": "customer",
      "is_verified": false
    }
  }
}
```

### 3. Create Parcel Delivery Request
`POST /api/v1/parcels`
*Header: `Authorization: Bearer <access_token>`*
```json
{
  "sender_name": "Rahim Ahmed",
  "sender_phone": "01711223344",
  "sender_address": "House 12, Road 4, Dhanmondi, Dhaka",
  "receiver_name": "Karim Hossain",
  "receiver_phone": "01811998877",
  "receiver_address": "Flat 3B, Nasirabad, Chittagong",
  "pickup_address": "House 12, Road 4, Dhanmondi, Dhaka",
  "delivery_address": "Flat 3B, Nasirabad, Chittagong",
  "parcel_type": "small_package",
  "parcel_weight": 2.5,
  "cod_amount": 1500.0,
  "parcel_description": "Electronics adapter",
  "special_instruction": "Handle with care, call before delivery"
}
```
Response (`201 Created`):
```json
{
  "id": 1,
  "tracking_number": "SWC8C94A0C7EB4A5FF120",
  "customer_id": 2,
  "agent_id": null,
  "sender_name": "Rahim Ahmed",
  "sender_phone": "01711223344",
  "sender_address": "House 12, Road 4, Dhanmondi, Dhaka",
  "receiver_name": "Karim Hossain",
  "receiver_phone": "01811998877",
  "receiver_address": "Flat 3B, Nasirabad, Chittagong",
  "pickup_address": "House 12, Road 4, Dhanmondi, Dhaka",
  "delivery_address": "Flat 3B, Nasirabad, Chittagong",
  "parcel_type": "small_package",
  "parcel_weight": 2.5,
  "parcel_description": "Electronics adapter",
  "special_instruction": "Handle with care, call before delivery",
  "delivery_charge": 80.0,
  "cod_amount": 1500.0,
  "payment_status": "pending",
  "delivery_status": "pending",
  "created_at": "2026-11-03T14:50:00Z",
  "updated_at": "2026-11-03T14:50:00Z"
}
```

### 4. Public Tracking
`GET /api/v1/tracking/SWC8C94A0C7EB4A5FF120`
*(No authorization required)*
```json
{
  "tracking_number": "SWC8C94A0C7EB4A5FF120",
  "delivery_status": "in_transit",
  "sender_name": "Rahim Ahmed",
  "receiver_name": "Karim Hossain",
  "pickup_address": "House 12, Road 4, Dhanmondi, Dhaka",
  "delivery_address": "Flat 3B, Nasirabad, Chittagong",
  "history": [
    {
      "id": 1,
      "old_status": null,
      "new_status": "pending",
      "note": null,
      "created_at": "2026-11-03T14:50:00Z"
    },
    {
      "id": 2,
      "old_status": "pending",
      "new_status": "confirmed",
      "note": "Verified by Dispatch",
      "created_at": "2026-11-03T15:00:00Z"
    },
    {
      "id": 3,
      "old_status": "confirmed",
      "new_status": "assigned",
      "note": "Assigned to agent #3",
      "created_at": "2026-11-03T15:10:00Z"
    },
    {
      "id": 4,
      "old_status": "assigned",
      "new_status": "picked_up",
      "note": "Picked up from sender",
      "created_at": "2026-11-03T15:30:00Z"
    },
    {
      "id": 5,
      "old_status": "picked_up",
      "new_status": "in_transit",
      "note": "On hub transit",
      "created_at": "2026-11-03T16:00:00Z"
    }
  ]
}
```

---

## 13. Frontend (React) Integration Guide

### 1. Axios Instance Setup
In your React app (`src/services/Api.jsx`):
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Attach access token to every outgoing request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Automatic token refresh interceptor on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(
            `${api.defaults.baseURL}/api/v1/auth/refresh`,
            { refresh_token: refreshToken }
          );
          const { access_token, refresh_token: newRefreshToken } = res.data.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshErr) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## 14. Production Deployment Checklist

Before deploying SwiftCourier to production:

- [ ] **Security Secret**: Replace `SECRET_KEY` with a securely generated 64-character random string.
- [ ] **Debug Mode**: Ensure `DEBUG=False` in your production environment variables.
- [ ] **PostgreSQL**: Set `DATABASE_URL` to your production Supabase database with connection pooling enabled.
- [ ] **Alembic**: Run `python -m alembic upgrade head` as part of your CI/CD deployment pipeline.
- [ ] **CORS**: Set `ALLOWED_ORIGINS` to the exact production frontend domains (e.g., `https://swiftcourier.app`).
- [ ] **HTTPS / TLS**: Always enforce TLS 1.3 / HTTPS termination via your reverse proxy (Nginx, Traefik, or Cloudflare).
- [ ] **Rate Limiting**: Put the API behind an API Gateway or reverse proxy rate-limiting filter.
- [ ] **Payment Provider**: Replace mock payment logic in `app/services/payment_service.py` with real webhook listeners and signature verification for Stripe, SSLCommerz, or bKash.
- [ ] **Email Provider**: Connect `auth_service.py`'s password reset and email verification tokens to an SMTP/SES/SendGrid mailer.
