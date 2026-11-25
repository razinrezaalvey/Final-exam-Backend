"""Tracking number generator and parcel utilities."""

import secrets
import string
import uuid


def generate_tracking_number() -> str:
    """
    Generate a unique, unpredictable tracking number.

    Format: SWC-XXXXXXXXXXXXXXXX (18 hex chars = 72 bits of entropy).
    """
    random_hex = secrets.token_hex(9).upper()
    return f"SWC{random_hex}"


def generate_idempotency_key() -> str:
    """Generate a UUID4-based idempotency key."""
    return str(uuid.uuid4())
