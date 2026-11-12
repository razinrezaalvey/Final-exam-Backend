from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, sessionLocal
import models
from deps import hash_password
from router import auth, users, parcels, agents, admin

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SwiftCourier API")

# CORS — must have allow_credentials=False when allow_origins=["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(parcels.router, prefix="/api/v1", tags=["Parcels"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def seed_defaults():
    """Seed default users and platform settings on first run."""
    db = sessionLocal()
    try:
        # Seed users
        seed_users = [
            ("Admin User", "admin@swiftcourier.com", "01700000000", "Admin12345", "admin"),
            ("Agent User", "agent@swiftcourier.com", "01800000000", "Agent12345", "agent"),
            ("Customer User", "customer@swiftcourier.com", "01900000000", "Customer12345", "customer"),
        ]
        for name, email, phone, pwd, role in seed_users:
            existing = db.query(models.User).filter(models.User.email == email).first()
            if not existing:
                u = models.User(
                    full_name=name,
                    email=email,
                    phone=phone,
                    hashed_password=hash_password(pwd),
                    role=role,
                    is_verified=True,
                )
                db.add(u)
                db.commit()
                db.refresh(u)
                if role == "agent":
                    db.add(models.AgentProfile(user_id=u.id, vehicle_type="motorcycle"))
                    db.commit()

        # Seed default settings
        defaults = [
            ("delivery_charge", "60", "Base delivery charge in BDT"),
            ("cod_charge_percent", "1", "COD charge percentage"),
            ("platform_name", "SwiftCourier", "Platform name"),
        ]
        for key, value, desc in defaults:
            if not db.query(models.PlatformSetting).filter(models.PlatformSetting.setting_key == key).first():
                db.add(models.PlatformSetting(setting_key=key, setting_value=value, description=desc))

        db.commit()
    finally:
        db.close()
