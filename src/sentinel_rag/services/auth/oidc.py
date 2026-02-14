"""
OpenID Connect (OIDC) authentication service.
Handles token creation, verification, and user context extraction.
Supports both user-based OIDC tokens and M2M client credential tokens.

"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JoseError

from .schemas import TenantConfig, UserContext
from sentinel_rag.config import AppSettings


oauth = OAuth()


def create_access_token(
    data: dict,
    settings: AppSettings,
    expires_delta: Optional[timedelta] = None,
    is_m2m: bool = False,
):
    """
    Create a JWT access token with the provided data.

    Args:
        data: Payload to encode in the token (user_id, email, tenant_id, role, department)
        settings: Application settings containing security configuration
        expires_delta: Optional custom expiration time
        is_m2m: Flag indicating if this is an M2M token

    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        default_minutes = (
            settings.security.access_token_expire_minutes * 60  # 60x longer for M2M
            if is_m2m
            else settings.security.access_token_expire_minutes
        )
        expire = datetime.now(timezone.utc) + timedelta(minutes=default_minutes)

    to_encode.update({"exp": expire, "is_m2m": is_m2m})

    encoded_jwt = jwt.encode(
        {"alg": settings.security.algorithm}, to_encode, settings.security.secret_key
    )
    return encoded_jwt.decode("utf-8")


def verify_token(token: str, settings: AppSettings) -> UserContext:
    """
    Verify and decode a JWT access token.
    Works for both user OIDC tokens and M2M client credential tokens.

    Args:
        token: JWT token to verify
        settings: Application settings containing security configuration

    Returns:
        UserContext with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        claims = jwt.decode(token, settings.security.secret_key)
        claims.validate()

        return UserContext(
            user_id=claims["user_id"],
            email=claims["sub"],
            tenant_id=claims["tenant_id"],
            role=claims["role"],
            department=claims["department"],
        )
    except (JoseError, KeyError) as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


# --- Dependency ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_active_user(
    request: Request, settings: AppSettings
) -> UserContext:
    """
    Extract and validate user authentication from request.

    Args:
        request: FastAPI request object
        settings: Application settings for token verification

    Returns:
        UserContext with authenticated user information
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
        user_context = verify_token(token, settings)
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
