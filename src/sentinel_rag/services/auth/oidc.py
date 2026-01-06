import os
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JoseError

from .models import TenantConfig, UserContext


# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

oauth = OAuth()

# --- JWT Management ---


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})

    # Authlib jwt.encode returns bytes, we need string
    encoded_jwt = jwt.encode({"alg": ALGORITHM}, to_encode, SECRET_KEY)
    return encoded_jwt.decode("utf-8")


def verify_token(token: str) -> UserContext:
    try:
        claims = jwt.decode(token, SECRET_KEY)
        claims.validate()

        return UserContext(
            user_id=claims["user_id"],
            email=claims["sub"],
            tenant_id=claims["tenant_id"],
            roles=claims["roles"],
            department=claims["department"],
        )
    except (JoseError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token")


# --- Dependency ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_active_user(request: Request) -> UserContext:
    """
    Authentication token resolution priority:
    1. Authorization header (Bearer token) - for API clients
    2. Cookie (access_token) - for browser SPAs
    """
    token = None

    # Priority 1: Check Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # Priority 2: Fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_context = verify_token(token)
        return user_context

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


# --- Client Registration ---


def register_tenant_client(tenant_config: TenantConfig):
    if isinstance(tenant_config, dict):
        tenant_config = TenantConfig(**tenant_config)

    client_name = tenant_config.tenant_id
    try:
        client = oauth.create_client(client_name)
        if client:
            return client
    except (AttributeError, RuntimeError):
        pass

    # Register new client if it doesn't exist
    oauth.register(
        name=client_name,
        client_id=tenant_config.oidc_config.client_id,
        client_secret=tenant_config.oidc_config.client_secret,
        server_metadata_url=tenant_config.oidc_config.server_metadata_url,
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth.create_client(client_name)
