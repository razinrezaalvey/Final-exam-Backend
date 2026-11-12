from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from deps import get_db
from router.auth import get_current_user
import models

router = APIRouter()


def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    return current_user


# ---------- Dashboard ----------

@router.get("/admin/dashboard")
def admin_dashboard(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    total_parcels = db.query(models.Parcel).count()
    total_customers = db.query(models.User).filter(models.User.role == "customer").count()
    total_agents = db.query(models.User).filter(models.User.role == "agent").count()
    delivered = db.query(models.Parcel).filter(models.Parcel.status == "delivered").count()
    pending = db.query(models.Parcel).filter(models.Parcel.status == "pending").count()
    active_deliveries = db.query(models.Parcel).filter(
        models.Parcel.status.in_(["in_transit", "picked_up", "out_for_delivery", "assigned"])
    ).count()
    total_revenue = delivered * 60.0

    data = {
        "total_parcels": total_parcels,
        "total_customers": total_customers,
        "total_agents": total_agents,
        "total_revenue": total_revenue,
        "pending_parcels": pending,
        "active_deliveries": active_deliveries,
        "delivered_parcels": delivered,
    }
    return {
        **data,
        "success": True,
        "data": data,
    }


# ---------- Reports ----------

@router.get("/reports/summary")
def reports_summary(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    total_parcels = db.query(models.Parcel).count()
    delivered = db.query(models.Parcel).filter(models.Parcel.status == "delivered").count()
    pending = db.query(models.Parcel).filter(models.Parcel.status == "pending").count()
    in_transit = db.query(models.Parcel).filter(
        models.Parcel.status.in_(["in_transit", "picked_up", "out_for_delivery"])
    ).count()
    cancelled = db.query(models.Parcel).filter(models.Parcel.status == "cancelled").count()
    total_agents = db.query(models.User).filter(models.User.role == "agent").count()
    total_customers = db.query(models.User).filter(models.User.role == "customer").count()
    total_revenue = delivered * 60.0

    overview = {
        "total_revenue": total_revenue,
        "total_parcels": total_parcels,
        "delivered_parcels": delivered,
        "pending_parcels": pending,
        "active_deliveries": in_transit,
    }

    breakdown = {
        "pending": pending,
        "picked_up": db.query(models.Parcel).filter(models.Parcel.status == "picked_up").count(),
        "in_transit": db.query(models.Parcel).filter(models.Parcel.status == "in_transit").count(),
        "delivered": delivered,
        "cancelled": cancelled,
    }

    return {
        "success": True,
        "data": {
            "overview": overview,
            "parcel_status_breakdown": breakdown,
            "total_parcels": total_parcels,
            "delivered": delivered,
            "pending": pending,
            "in_transit": in_transit,
            "cancelled": cancelled,
            "total_agents": total_agents,
            "total_customers": total_customers,
            "total_revenue": total_revenue,
        },
    }


# ---------- Payments ----------

@router.get("/payments")
def list_payments(
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    parcels = (
        db.query(models.Parcel)
        .order_by(models.Parcel.created_at.desc())
        .limit(page_size)
        .all()
    )
    payments = [
        {
            "id": p.id,
            "parcel_id": p.id,
            "tracking_number": p.tracking_number,
            "amount": (p.cod_amount or 0) + 60.0,
            "payment_method": "Cash on Delivery",
            "payment_status": "completed" if p.status == "delivered" else "pending",
            "status": "paid" if p.status == "delivered" else "pending",
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in parcels
    ]
    return {"success": True, "data": payments}


# ---------- Platform Settings ----------

@router.get("/settings")
def list_settings(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    settings = db.query(models.PlatformSetting).all()
    # Frontend specifically checks `Array.isArray(settingsRes.value.data)`
    return [
        {"setting_key": s.setting_key, "setting_value": s.setting_value}
        for s in settings
    ]


@router.get("/settings/{key}")
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    setting = db.query(models.PlatformSetting).filter(
        models.PlatformSetting.setting_key == key
    ).first()
    if not setting:
        return {"success": True, "data": {"key": key, "value": ""}}
    return {"success": True, "data": {"key": setting.setting_key, "value": setting.setting_value}}


class SettingUpdateRequest(BaseModel):
    value: str


@router.put("/settings/{key}")
def update_setting(
    key: str,
    body: SettingUpdateRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    setting = db.query(models.PlatformSetting).filter(
        models.PlatformSetting.setting_key == key
    ).first()
    if not setting:
        setting = models.PlatformSetting(setting_key=key, setting_value=body.value)
        db.add(setting)
    else:
        setting.setting_value = body.value
    db.commit()
    return {"success": True, "data": {"key": key, "value": body.value}}
