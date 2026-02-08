import asyncpg
from os import path as os_path
from typing import Optional


class AuditDatabaseManager:
    """Manages audit database connection pool and schema initialization."""

    def __init__(
        self,
        database_url: str,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
    ):
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        await self._init_schema()
        await self._create_pool()

    async def _init_schema(self) -> None:
        try:
            schema_path = os_path.join(os_path.dirname(__file__), "audit_schema.sql")
            with open(schema_path, "r") as f:
                schema_sql = f.read()
        except Exception as e:
            raise RuntimeError(f"Error reading audit schema file: {e}")

        # Create a temporary connection to execute schema
        conn = await asyncpg.connect(self.database_url)
        try:
            await conn.execute(schema_sql)
            print("✓ Audit database tables initialized.")
        except Exception as e:
            raise RuntimeError(f"Error initializing audit database tables: {e}")
        finally:
            await conn.close()

    async def _create_pool(self) -> None:
        """Create asyncpg connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
                command_timeout=60,
            )
            print(
                f"✓ Audit database pool created (min={self.min_pool_size}, max={self.max_pool_size})"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create audit database pool: {e}")

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the connection pool."""
        if self._pool is None:
            raise RuntimeError(
                "Database pool not initialized. Call initialize() first."
            )
        return self._pool

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            print("✓ Audit database pool closed.")
