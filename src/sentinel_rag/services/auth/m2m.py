"""
M2M (Machine-to-Machine) Authentication utilities.
Handles client credentials flow for programmatic API access.
"""

import secrets
import bcrypt
from datetime import datetime, timezone
from typing import Tuple
from fastapi import HTTPException

from sentinel_rag.services.database import DatabaseManager


def generate_client_secret() -> str:
    return f"cs_{secrets.token_urlsafe(32)}"


def hash_client_secret(secret: str) -> str:
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_client_secret(secret: str, secret_hash: str) -> bool:
    try:
        return bcrypt.checkpw(secret.encode("utf-8"), secret_hash.encode("utf-8"))
    except Exception:
        return False


def authenticate_m2m_client(
    client_id: str,
    client_secret: str,
    db: DatabaseManager,
    tenant_id: str,
) -> Tuple[str, str, str, str, str]:
    client_data = db.get_m2m_client_with_user_info(client_id)

    if not client_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid client credentials",
        )

    if not client_data["is_active"]:
        raise HTTPException(
            status_code=401,
            detail="Client has been revoked",
        )

    if client_data["expires_at"]:
        if datetime.now(timezone.utc) > client_data["expires_at"].replace(
            tzinfo=timezone.utc
        ):
            raise HTTPException(
                status_code=401,
                detail="Client credentials have expired",
            )

    if not verify_client_secret(client_secret, client_data["client_secret_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid client credentials",
        )

    # Ensure client has associated user
    if not client_data.get("user_id"):
        raise HTTPException(
            status_code=500,
            detail="Client has no associated user account",
        )

    if not client_data.get("role_name") or not client_data.get("department_name"):
        raise HTTPException(
            status_code=403,
            detail="Client's associated user has no role/department. Contact administrator.",
        )

    # Update last used timestamp
    db.update_m2m_client_last_used(client_id)

    return (
        str(client_data["user_id"]),
        client_data["email"],
        client_data["role_name"],
        client_data["department_name"],
        client_id,
    )
