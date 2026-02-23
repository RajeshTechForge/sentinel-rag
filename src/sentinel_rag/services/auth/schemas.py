from uuid import UUID
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class OIDCConfig(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str


class TenantConfig(BaseModel):
    tenant_id: str
    domain: str
    oidc_config: OIDCConfig


class UserContext(BaseModel):
    user_id: UUID
    email: EmailStr
    tenant_id: str
    role: str
    department: str


#          For M2M Authentication
# ------------------------------------------


class ClientCredentialsRequest(BaseModel):
    grant_type: str = Field(
        default="client_credentials", pattern="^client_credentials$"
    )
    client_id: str
    client_secret: str
    scope: Optional[str] = None  # Space-separated scopes


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    scope: Optional[str] = None


class M2MClientCreate(BaseModel):
    client_name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    service_account_user_id: Optional[UUID] = (
        None  # User whose permissions this client inherits
    )
    scopes: Optional[List[str]] = None
    expires_days: Optional[int] = None


class M2MClientCreated(BaseModel):
    client_id: UUID
    client_name: str
    client_secret: str
    description: Optional[str] = None
    scopes: Optional[List[str]] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    warning: str = "Store the client_secret securely. It will not be shown again."


class M2MClientInfo(BaseModel):
    # without secret
    client_id: UUID
    client_name: str
    description: Optional[str] = None
    owner_user_id: UUID
    service_account_user_id: Optional[UUID] = None
    is_active: bool
    scopes: Optional[List[str]] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class M2MTokenPayload(BaseModel):
    user_id: UUID
    email: EmailStr
    tenant_id: str
    role: str
    department: str
    client_id: Optional[UUID] = None  # Include client_id for M2M tokens
    is_m2m: bool = False
    scopes: Optional[List[str]] = None
