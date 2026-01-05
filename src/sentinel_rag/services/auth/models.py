from pydantic import BaseModel


class OIDCConfig(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str


class TenantConfig(BaseModel):
    tenant_id: str
    domain: str
    oidc_config: OIDCConfig


class UserContext(BaseModel):
    user_id: str
    email: str
    tenant_id: str
    role: str
    department: str
