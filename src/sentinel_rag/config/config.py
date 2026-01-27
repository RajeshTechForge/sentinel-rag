"""
Centralized Configuration Management using Pydantic Settings.

This module implements a hybrid configuration approach:
- Business logic configs (departments, roles, etc.) → JSON file
- Environment-specific secrets (DB credentials, API keys) → .env file
"""

import json
from os import path as os_path
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
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


class DocRetrievalSettings(BaseSettings):
    max_retrieved_docs: int = Field(default=20, ge=1, le=100)
    similarity_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    rrf_constant: int = Field(default=60, ge=1, le=100)

    use_parent_retrieval: bool = True
    parent_chunk_size: int = Field(default=2000, ge=500, le=8000)
    parent_chunk_overlap: int = Field(default=200, ge=0, le=1000)
    child_chunk_size: int = Field(default=400, ge=100, le=2000)
    child_chunk_overlap: int = Field(default=50, ge=0, le=500)


class EmbeddingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EMBEDDING_")

    provider: str = "fake"  # openai, gemini, fake
    model_name: str = ""  # Optional, provider defaults used if empty
    api_key: str = ""
    vector_size: int = 1536  # Dimension of embedding vectors


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QDRANT_")

    host: str = "localhost"
    port: int = 6333
    api_key: str = ""
    prefer_grpc: bool = True


class OIDCSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OIDC_")

    client_id: str = ""
    client_secret: str = ""
    server_metadata_url: str = ""


class TenantSettings(BaseSettings):
    tenant_id: str = Field(default="", alias="TENANT_ID")
    domain: str = Field(default="", alias="TENANT_DOMAIN")


class SecuritySettings(BaseSettings):
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
    enabled: bool = False
    retention_years: int = Field(default=7, ge=1, le=20)
    async_logging: bool = True


class RBACSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="allow")

    departments: list[str] = Field(default_factory=list)
    roles: dict[str, list[str]] = Field(default_factory=dict)
    access_matrix: dict[str, dict[str, list[str]]] = Field(default_factory=dict)

    @property
    def as_dict(self) -> dict:
        return {
            "departments": self.departments,
            "roles": self.roles,
            "access_matrix": self.access_matrix,
        }


class CORSSettings(BaseSettings):
    allow_origins: list[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE"]
    allow_headers: list[str] = ["*"]


class AppSettings(BaseSettings):
    """
    Main application settings aggregating all configuration.

    Implements hybrid configuration loading:
    1. Loads SENTINEL_CONFIG_PATH from .env
    2. Reads business logic config from JSON file (app metadata, RBAC)
    3. Loads secrets/env-specific config from .env (database, OIDC, security)

    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Path to JSON config file (from .env)
    config_path: str = Field(
        default="../../../config/config.json", alias="SENTINEL_CONFIG_PATH"
    )

    # Application metadata (from JSON)
    app_name: str = "Sentinel RAG API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    doc_retrieval: DocRetrievalSettings = Field(default_factory=DocRetrievalSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    oidc: OIDCSettings = Field(default_factory=OIDCSettings)
    tenant: TenantSettings = Field(default_factory=TenantSettings)
    security: SecuritySettings = Field(
        default_factory=lambda: SecuritySettings(
            secret_key="change-me-in-production-32-chars"
        )
    )
    audit: AuditSettings = Field(default_factory=AuditSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)

    rbac: RBACSettings = Field(default_factory=RBACSettings)

    @model_validator(mode="after")
    def load_json_config(self) -> "AppSettings":
        """
        Load configuration from JSON file after .env is loaded.

        """
        config_file = self._resolve_config_path()

        # Load JSON configuration
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                json_config = json.load(f)

            self.app_name = json_config.get("APP_NAME", self.app_name)
            self.app_version = json_config.get("APP_VERSION", self.app_version)
            self.environment = json_config.get("APP_ENV", self.environment)
            self.debug = self._parse_bool(json_config.get("DEBUG", self.debug))
            self.audit.enabled = self._parse_bool(
                json_config.get("ENABLE_AUDIT_LOGGING", self.audit.enabled)
            )

            # Load document retrieval settings
            doc_retrieval_cfg = json_config.get("DOC_RETRIEVAL_SETTINGS", {})
            self.doc_retrieval.max_retrieved_docs = doc_retrieval_cfg.get(
                "max_retrieved_docs", self.doc_retrieval.max_retrieved_docs
            )
            self.doc_retrieval.similarity_threshold = doc_retrieval_cfg.get(
                "similarity_threshold", self.doc_retrieval.similarity_threshold
            )
            self.doc_retrieval.rrf_constant = doc_retrieval_cfg.get(
                "rrf_constant", self.doc_retrieval.rrf_constant
            )

            # Parent-Document Retrieval settings
            self.doc_retrieval.use_parent_retrieval = self._parse_bool(
                doc_retrieval_cfg.get(
                    "use_parent_retrieval", self.doc_retrieval.use_parent_retrieval
                )
            )
            self.doc_retrieval.parent_chunk_size = doc_retrieval_cfg.get(
                "parent_chunk_size", self.doc_retrieval.parent_chunk_size
            )
            self.doc_retrieval.parent_chunk_overlap = doc_retrieval_cfg.get(
                "parent_chunk_overlap", self.doc_retrieval.parent_chunk_overlap
            )
            self.doc_retrieval.child_chunk_size = doc_retrieval_cfg.get(
                "child_chunk_size", self.doc_retrieval.child_chunk_size
            )
            self.doc_retrieval.child_chunk_overlap = doc_retrieval_cfg.get(
                "child_chunk_overlap", self.doc_retrieval.child_chunk_overlap
            )

            # Load RBAC configuration
            self.rbac.departments = json_config.get("DEPARTMENTS", [])
            self.rbac.roles = json_config.get("ROLES", {})
            self.rbac.access_matrix = json_config.get("ACCESS_MATRIX", {})

            print(f"✓ Loaded configuration from: {config_file}")

        except FileNotFoundError:
            print(f"WARNING: Config file not found: {config_file}. Using defaults.")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in config file {config_file}: {e}")
            raise ValueError(f"Invalid JSON configuration file: {config_file}") from e

        return self

    def _resolve_config_path(self) -> str:
        """Resolve the configuration file path with fallback logic."""
        if self.config_path and os_path.exists(self.config_path):
            return self.config_path

        # Fallback to default.json in the same directory
        default_path = os_path.join(os_path.dirname(__file__), "default.json")
        if os_path.exists(default_path):
            print(f"INFO: Using default config at {default_path}")
            return default_path

        raise FileNotFoundError(
            f"No valid config file found. Tried: {self.config_path}, {default_path}"
        )

    @staticmethod
    def _parse_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        if isinstance(value, int):
            return bool(value)
        return False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
