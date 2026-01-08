"""
Centralized Configuration Management using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "localhost"
    port: int = 5432
    database: str = Field(alias="POSTGRES_DB", default="sample_db")
    user: str = "postgres"
    password: str = ""
    min_pool_size: int = Field(default=5, ge=1, le=20)
    max_pool_size: int = Field(default=10, ge=5, le=100)

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class OIDCSettings(BaseSettings):
    """OIDC/OAuth2 configuration."""

    model_config = SettingsConfigDict(env_prefix="OIDC_")

    client_id: str = ""
    client_secret: str = ""
    server_metadata_url: str = ""


class TenantSettings(BaseSettings):
    """Tenant configuration."""

    tenant_id: str = Field(default="", alias="TENANT_ID")
    domain: str = Field(default="", alias="TENANT_DOMAIN")


class SecuritySettings(BaseSettings):
    """Security-related settings."""

    model_config = SettingsConfigDict(populate_by_name=True)

    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v


class AuditSettings(BaseSettings):
    """Audit logging configuration."""

    enabled: bool = Field(default=False, alias="ENABLE_AUDIT_LOGGING")
    retention_years: int = Field(default=7, ge=1, le=20)
    async_logging: bool = True


class CORSSettings(BaseSettings):
    """CORS configuration."""

    allow_origins: list[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE"]
    allow_headers: list[str] = ["*"]


class AppSettings(BaseSettings):
    """
    Main application settings aggregating all configuration.

    Usage:
        settings = get_settings()
        print(settings.database.host)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application metadata
    app_name: str = "Sentinel RAG API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", alias="APP_ENV")

    # Config file path
    config_path: Optional[str] = Field(default=None, alias="SENTINEL_CONFIG_PATH")

    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    oidc: OIDCSettings = Field(default_factory=OIDCSettings)
    tenant: TenantSettings = Field(default_factory=TenantSettings)
    security: SecuritySettings = Field(
        default_factory=lambda: SecuritySettings(
            secret_key="change-me-in-production-32-chars"
        )
    )
    audit: AuditSettings = Field(default_factory=AuditSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> AppSettings:
    """
    Cached settings factory.

    The @lru_cache ensures settings are loaded only once.
    For testing, use dependency injection override.
    """
    return AppSettings()
