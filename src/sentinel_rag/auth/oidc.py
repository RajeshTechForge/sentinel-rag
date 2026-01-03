import os
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JoseError
from starlette.config import Config

from sentinel_rag.auth.models import UserContext, TokenData
from sentinel_rag.auth.tenant_config import get_tenant_config_by_domain, TenantConfig

# --- Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Initialize Authlib
oauth = OAuth()

# --- RBAC Mapping ---
# This could be loaded from a DB or config file per tenant
GROUP_ROLE_MAPPING = {
    "tenant_acme": {
        "Admins": "admin",
        "Engineers": "editor",
        "Viewers": "viewer"
    },
    "tenant_globex": {
        "IT_Admin": "admin",
        "Staff": "viewer"
    }
}

def map_idp_groups_to_roles(tenant_id: str, idp_groups: List[str]) -> List[str]:
    """
    Maps IdP groups (e.g., 'Admins') to internal roles (e.g., 'admin').
    """
    mapping = GROUP_ROLE_MAPPING.get(tenant_id, {})
    roles = set()
    for group in idp_groups:
        if group in mapping:
            roles.add(mapping[group])
    
    # Default role if no mapping found
    if not roles:
        roles.add("viewer")
        
    return list(roles)

# --- JWT Management ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    
    # Authlib jwt.encode returns bytes, we need string
    encoded_jwt = jwt.encode({"alg": ALGORITHM}, to_encode, SECRET_KEY)
    return encoded_jwt.decode('utf-8')

def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY)
        payload.validate() # Checks exp, etc.
        email: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if email is None or tenant_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        return TokenData(email=email, tenant_id=tenant_id)
    except JoseError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

# --- Dependency ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_current_active_user(request: Request) -> UserContext:
    # Try to get token from cookie first (HttpOnly), then Authorization header
    token = request.cookies.get("access_token")
    if not token:
        # Fallback to header if needed (e.g. for programmatic access)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    token_data = verify_token(token)
    
    # We might fetch fresh user data from DB here
    # For now, we trust the token claims if we put roles in there, 
    # OR we re-fetch roles. Let's assume we put roles in the token for statelessness 
    # or we just re-construct the context.
    
    # Let's decode again to get roles (verify_token only returned minimal data)
    payload = jwt.decode(token, SECRET_KEY)
    roles = payload.get("roles", [])
    department = payload.get("department")
    user_id = payload.get("user_id")

    return UserContext(
        user_id=user_id,
        email=token_data.email,
        tenant_id=token_data.tenant_id,
        roles=roles,
        department=department
    )

# --- Dynamic Client Registration ---

def register_tenant_client(tenant_config: TenantConfig):
    """
    Registers an OAuth client for the specific tenant if not already registered.
    """
    client_name = tenant_config.tenant_id
    if not oauth.create_client(client_name):
        oauth.register(
            name=client_name,
            client_id=tenant_config.oidc_config.client_id,
            client_secret=tenant_config.oidc_config.client_secret,
            server_metadata_url=tenant_config.oidc_config.server_metadata_url,
            client_kwargs=tenant_config.oidc_config.client_kwargs
        )
    return oauth.create_client(client_name)
