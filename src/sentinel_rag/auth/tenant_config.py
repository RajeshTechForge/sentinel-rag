from pydantic import BaseModel
from typing import Dict, Optional

class OIDCConfig(BaseModel):
    client_id: str
    client_secret: str
    server_metadata_url: str
    client_kwargs: Dict[str, str] = {"scope": "openid email profile groups"}

class TenantConfig(BaseModel):
    tenant_id: str
    domain: str
    oidc_config: OIDCConfig

# Mock Tenant Registry
# In a real system, this would come from a database or secrets manager
TENANT_REGISTRY: Dict[str, TenantConfig] = {
    "acme.com": TenantConfig(
        tenant_id="tenant_acme",
        domain="acme.com",
        oidc_config=OIDCConfig(
            client_id="mock_acme_client_id",
            client_secret="mock_acme_secret",
            server_metadata_url="https://dev-123456.okta.com/.well-known/openid-configuration"
        )
    ),
    "globex.com": TenantConfig(
        tenant_id="tenant_globex",
        domain="globex.com",
        oidc_config=OIDCConfig(
            client_id="mock_globex_client_id",
            client_secret="mock_globex_secret",
            server_metadata_url="https://globex.auth0.com/.well-known/openid-configuration"
        )
    )
}

def get_tenant_config_by_domain(domain: str) -> Optional[TenantConfig]:
    return TENANT_REGISTRY.get(domain)

def get_tenant_config_by_id(tenant_id: str) -> Optional[TenantConfig]:
    for config in TENANT_REGISTRY.values():
        if config.tenant_id == tenant_id:
            return config
    return None
