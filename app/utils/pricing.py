"""Delivery pricing calculation utilities."""

from sqlalchemy.orm import Session
from app.models.platform_setting import PlatformSetting


DEFAULT_BASE_CHARGE = 50.0
DEFAULT_PER_KG_CHARGE = 10.0
DEFAULT_COD_CHARGE_PCT = 1.0


def get_setting_float(db: Session, key: str, default: float) -> float:
    """Fetch a numeric platform setting, falling back to default."""
    setting = db.query(PlatformSetting).filter(
        PlatformSetting.setting_key == key
    ).first()
    if setting:
        try:
            return float(setting.setting_value)
        except (ValueError, TypeError):
            pass
    return default


def calculate_delivery_charge(
    db: Session,
    weight_kg: float,
    cod_amount: float = 0.0,
    zone: str = "standard",
) -> float:
    """
    Calculate delivery charge based on configurable pricing rules.

    Pricing logic:
    - base_charge: flat charge for any delivery
    - per_kg_charge: extra per kg (above first kg)
    - cod_charge_pct: percentage of COD amount added as fee
    - zone multipliers: express/remote zones cost more

    All rules are configurable via platform settings.
    """
    base_charge = get_setting_float(db, "base_delivery_charge", DEFAULT_BASE_CHARGE)
    per_kg_charge = get_setting_float(db, "per_kg_charge", DEFAULT_PER_KG_CHARGE)
    cod_charge_pct = get_setting_float(db, "cod_charge_percentage", DEFAULT_COD_CHARGE_PCT)

    zone_multipliers = {
        "standard": 1.0,
        "express": 1.5,
        "remote": 2.0,
    }
    multiplier = zone_multipliers.get(zone, 1.0)

    weight_charge = 0.0
    if weight_kg > 1.0:
        weight_charge = (weight_kg - 1.0) * per_kg_charge

    cod_fee = (cod_amount * cod_charge_pct / 100.0) if cod_amount > 0 else 0.0

    total = (base_charge + weight_charge + cod_fee) * multiplier
    return round(total, 2)
