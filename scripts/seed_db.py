"""Database seeding script for SwiftCourier.

Creates default platform settings and an initial admin user if not present.

Usage:
    python scripts/seed_db.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.platform_setting import PlatformSetting
from app.core.security import hash_password


DEFAULT_SETTINGS = [
    {
        "setting_key": "base_delivery_charge",
        "setting_value": "50.00",
        "description": "Base delivery fee applied to every shipment",
    },
    {
        "setting_key": "per_kg_charge",
        "setting_value": "10.00",
        "description": "Extra fee per kg for weights exceeding 1 kg",
    },
    {
        "setting_key": "cod_charge_percentage",
        "setting_value": "1.0",
        "description": "Percentage surcharge for Cash on Delivery orders",
    },
    {
        "setting_key": "agent_commission_percentage",
        "setting_value": "10.0",
        "description": "Percentage of delivery charge credited to agent on successful delivery",
    },
]


def seed():
    db = SessionLocal()
    try:
        for s in DEFAULT_SETTINGS:
            existing = db.query(PlatformSetting).filter(
                PlatformSetting.setting_key == s["setting_key"]
            ).first()
            if not existing:
                setting = PlatformSetting(
                    setting_key=s["setting_key"],
                    setting_value=s["setting_value"],
                    description=s["description"],
                )
                db.add(setting)
                print(f"Added setting: {s['setting_key']} = {s['setting_value']}")

        admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@swiftcourier.com")
        admin_pass = os.getenv("INITIAL_ADMIN_PASSWORD", "Admin12345")

        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin = User(
                full_name="System Administrator",
                email=admin_email,
                hashed_password=hash_password(admin_pass),
                phone="01700000000",
                role=UserRole.admin,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            print(f"Created initial admin user: {admin_email} (password: {admin_pass})")
        else:
            print(f"Admin user already exists: {admin_email}")

        db.commit()
        print("Database seeding completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

