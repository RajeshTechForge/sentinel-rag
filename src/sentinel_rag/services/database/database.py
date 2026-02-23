"""
DatabaseManager: Manages PostgreSQL database interactions for user, department,
role, and document metadata management, including full-text search for hybrid retrieval.

Vector operations are handled separately by QdrantStore.
"""

from contextlib import contextmanager
from os import path as os_path
from typing import List, Optional, Dict

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json, execute_batch

from .exceptions import DatabaseError


class DatabaseManager:
    _MIN_POOL_SIZE = 2
    _MAX_POOL_SIZE = 10

    def __init__(self, database_url: str):
        self.connection_params = psycopg2.extensions.parse_dsn(database_url)
        self._pool = None
        self._init_tables()
        self._init_pool()

    def _init_pool(self):
        """Initialize connection pool."""
        try:
            self._pool = pool.ThreadedConnectionPool(
                self._MIN_POOL_SIZE, self._MAX_POOL_SIZE, **self.connection_params
            )
        except Exception as e:
            raise DatabaseError(f"Failed to initialize connection pool: {e}")

    @contextmanager
    def _get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except Exception as e:
            raise DatabaseError(f"Database connection error: {e}")
        finally:
            if conn:
                self._pool.putconn(conn)

    def _init_tables(self):
        """Initialize database tables from schema.sql."""
        try:
            schema_path = os_path.join(os_path.dirname(__file__), "schema.sql")
            with open(schema_path, "r") as f:
                schema_sql = f.read()
        except Exception as e:
            raise DatabaseError(f"Error reading database schema file: {e}")

        conn = psycopg2.connect(**self.connection_params)
        try:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
        except Exception as e:
            raise DatabaseError(f"Error initializing database tables: {e}")
        finally:
            conn.close()
            print("Database tables initialized.")

    # ─────────────────────────────────────────────
    #              User Management
    # ─────────────────────────────────────────────
    def create_user(
        self,
        email: str,
        full_name: str,
        permission_level_id: str,
        department_id: Optional[str] = None,
        role_id: Optional[str] = None,
    ) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, full_name, permission_level_id, department_id, role_id) VALUES (%s, %s, %s, %s, %s) RETURNING user_id",
                    (email, full_name, permission_level_id, department_id, role_id),
                )
                user_id = cur.fetchone()[0]
            conn.commit()
        return str(user_id)

    def get_user_permission_level(self, user_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pl.permission_level_name 
                    FROM users u 
                    JOIN permission_levels pl ON u.permission_level_id = pl.permission_level_id
                    WHERE u.user_id = %s
                    """,
                    (user_id,),
                )
                res = cur.fetchone()
                return res[0] if res else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cur.fetchone()

    def get_user_role_and_department(self, user_id: str) -> Optional[tuple]:
        """Return (department_name, role_name) for a user or None if not assigned."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.department_name, r.role_name
                    FROM users u
                    LEFT JOIN departments d ON u.department_id = d.department_id
                    LEFT JOIN roles r ON u.role_id = r.role_id
                    WHERE u.user_id = %s
                    """,
                    (user_id,),
                )
                return cur.fetchone()

    def get_document_uploads_by_user(self, user_id: str) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT d.doc_id, d.filename, d.title, d.description, 
                           d.classification, d.created_at, dept.department_name
                    FROM documents d
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE d.uploaded_by = %s
                    ORDER BY d.created_at DESC
                    """,
                    (user_id,),
                )
                return cur.fetchall()

    # ─────────────────────────────────────────────
    #             RBAC Management
    # ─────────────────────────────────────────────

    def create_permission_level(self, permission_level_name: str) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO permission_levels (permission_level_name) VALUES (%s) ON CONFLICT (permission_level_name) DO NOTHING RETURNING permission_level_id",
                    (permission_level_name,),
                )
                res = cur.fetchone()
                if not res:
                    # If it existed, we need to fetch it
                    cur.execute(
                        "SELECT permission_level_id FROM permission_levels WHERE permission_level_name = %s",
                        (permission_level_name,),
                    )
                    permission_level_id = cur.fetchone()[0]
                else:
                    permission_level_id = res[0]
            conn.commit()
        return str(permission_level_id)

    def get_all_permission_levels(self) -> List[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT permission_level_name FROM permission_levels")
                return [row[0] for row in cur.fetchall()]

    def create_access_level(self, access_level_name: str) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO access_levels (access_level_name) VALUES (%s) ON CONFLICT (access_level_name) DO NOTHING RETURNING access_level_id",
                    (access_level_name,),
                )
                res = cur.fetchone()
                if not res:
                    # If it existed, we need to fetch it
                    cur.execute(
                        "SELECT access_level_id FROM access_levels WHERE access_level_name = %s",
                        (access_level_name,),
                    )
                    access_level_id = cur.fetchone()[0]
                else:
                    access_level_id = res[0]
            conn.commit()
        return str(access_level_id)

    def get_all_access_levels(self) -> List[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT access_level_name FROM access_levels")
                return [row[0] for row in cur.fetchall()]

    def assign_role_access(
        self, role_name: str, department_name: str, access_level_name: str
    ):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Get role_id
                cur.execute(
                    """
                    SELECT r.role_id 
                    FROM roles r 
                    JOIN departments d ON r.department_id = d.department_id 
                    WHERE r.role_name = %s AND d.department_name = %s
                """,
                    (role_name, department_name),
                )
                role_res = cur.fetchone()
                if not role_res:
                    raise ValueError(
                        f"Role '{role_name}' in department '{department_name}' not found"
                    )
                role_id = role_res[0]

                # Get access_level_id
                cur.execute(
                    "SELECT access_level_id FROM access_levels WHERE access_level_name = %s",
                    (access_level_name,),
                )
                access_res = cur.fetchone()
                if not access_res:
                    raise ValueError(f"Access level '{access_level_name}' not found")
                access_level_id = access_res[0]

                # Insert
                cur.execute(
                    """
                    INSERT INTO role_access (role_id, access_level_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT (role_id, access_level_id) DO NOTHING
                """,
                    (role_id, access_level_id),
                )
            conn.commit()

    def get_all_role_access(self) -> List[tuple]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.role_name, d.department_name, a.access_level_name
                    FROM role_access ra
                    JOIN roles r ON ra.role_id = r.role_id
                    JOIN departments d ON r.department_id = d.department_id
                    JOIN access_levels a ON ra.access_level_id = a.access_level_id
                """
                )
                return cur.fetchall()

    # ─────────────────────────────────────────────
    #             Department Management
    # ─────────────────────────────────────────────
    def create_department(self, department_name: str) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO departments (department_name) VALUES (%s) RETURNING department_id",
                    (department_name,),
                )
                department_id = cur.fetchone()[0]
            conn.commit()
        return str(department_id)

    def get_all_departments(self) -> List[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT department_name FROM departments")
                return [row[0] for row in cur.fetchall()]

    def get_user_department(self, user_id: str) -> Optional[str]:
        """Return the department name for a user or None if not assigned."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.department_name 
                    FROM users u
                    LEFT JOIN departments d ON u.department_id = d.department_id
                    WHERE u.user_id = %s
                    """,
                    (user_id,),
                )
                result = cur.fetchone()
                return result[0] if result else None

    def get_department_id_by_name(self, department_name: str) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT department_id FROM departments WHERE department_name = %s",
                    (department_name,),
                )
                res = cur.fetchone()
                return str(res[0]) if res else None

    def get_department_name_by_id(self, department_id: str) -> Optional[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT department_name FROM departments WHERE department_id = %s",
                    (department_id,),
                )
                res = cur.fetchone()
                return res[0] if res else None

    # ─────────────────────────────────────────────
    #               Role Management
    # ─────────────────────────────────────────────
    def create_role(self, role_name: str, department_name: str) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT department_id FROM departments WHERE department_name = %s",
                    (department_name,),
                )
                res = cur.fetchone()
                if not res:
                    raise ValueError(f"Department {department_name} not found")
                department_id = res[0]

                cur.execute(
                    "INSERT INTO roles (role_name, department_id) VALUES (%s, %s) RETURNING role_id",
                    (role_name, department_id),
                )
                role_id = cur.fetchone()[0]
            conn.commit()
        return str(role_id)

    def get_all_roles(self) -> List[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT r.role_name, d.department_name 
                    FROM roles r 
                    JOIN departments d ON r.department_id = d.department_id
                    """
                )
                return cur.fetchall()

    def get_roles_by_department(self, department_name: str) -> List[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.role_name 
                    FROM roles r 
                    JOIN departments d ON r.department_id = d.department_id
                    WHERE d.department_name = %s
                    """,
                    (department_name,),
                )
                return [row[0] for row in cur.fetchall()]

    # ─────────────────────────────────────────────
    #          Document Metadata Management
    # ─────────────────────────────────────────────
    def create_document(
        self,
        filename: str,
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        classification: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a document metadata entry."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents 
                    (filename, title, description, uploaded_by, department_id, classification, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id
                    """,
                    (
                        filename,
                        title,
                        description,
                        user_id,
                        department_id,
                        classification,
                        Json(metadata or {}),
                    ),
                )
                doc_id = cur.fetchone()[0]
            conn.commit()
        return str(doc_id)

    def save_chunk_metadata(
        self,
        doc_id: str,
        chunk_id: str,
        content: str,
        page_number: int,
        chunk_index: int,
        metadata: Optional[dict] = None,
        chunk_type: str = "child",
        parent_chunk_id: Optional[str] = None,
    ):
        """Save chunk metadata and content for full-text search."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO document_chunks 
                    (chunk_id, doc_id, content, page_number, chunk_index, chunk_type, parent_chunk_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO NOTHING
                    """,
                    (
                        chunk_id,
                        doc_id,
                        content,
                        page_number,
                        chunk_index,
                        chunk_type,
                        parent_chunk_id,
                        Json(metadata or {}),
                    ),
                )
            conn.commit()

    def save_chunks_batch(
        self,
        doc_id: str,
        chunk_ids: List[str],
        contents: List[str],
        page_numbers: List[int],
        chunk_indexes: List[int],
        metadatas: List[dict],
        chunk_types: Optional[List[str]] = None,
        parent_chunk_ids: Optional[List[str]] = None,
    ):
        """Batch save chunk metadata for full-text search."""
        if not chunk_ids:
            return

        chunk_types = chunk_types or ["child"] * len(chunk_ids)
        parent_chunk_ids = parent_chunk_ids or [None] * len(chunk_ids)

        insert_sql = """
            INSERT INTO document_chunks 
            (chunk_id, doc_id, content, page_number, chunk_index, chunk_type, parent_chunk_id, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (chunk_id) DO NOTHING
        """

        data = [
            (
                chunk_id,
                doc_id,
                content,
                page_num,
                chunk_idx,
                chunk_type,
                parent_id,
                Json(meta),
            )
            for chunk_id, content, page_num, chunk_idx, chunk_type, parent_id, meta in zip(
                chunk_ids,
                contents,
                page_numbers,
                chunk_indexes,
                chunk_types,
                parent_chunk_ids,
                metadatas,
            )
        ]

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, insert_sql, data, page_size=100)
            conn.commit()

    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT d.*, dept.department_name 
                    FROM documents d
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE d.doc_id = %s
                    """,
                    (doc_id,),
                )
                return cur.fetchone()

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its chunks."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
                deleted = cur.rowcount > 0
            conn.commit()
        return deleted

    # ─────────────────────────────────────────────
    #           Full-Text Search (Keyword)
    # ─────────────────────────────────────────────
    def keyword_search(
        self,
        query_text: str,
        filters: List[tuple],
        k: int = 20,
        chunk_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Perform full-text search with RBAC filtering.

        Args:
            query_text: Search query.
            filters: List of (department, classification) tuples for RBAC.
            k: Maximum results to return.
            chunk_type: Optional filter for 'parent' or 'child' chunks.

        Returns:
            List of chunk data with BM25 rank scores.
        """
        if not filters or not query_text.strip():
            return []

        where_clauses = []
        params = []
        for dept, cls in filters:
            where_clauses.append(
                "(dept.department_name = %s AND d.classification = %s)"
            )
            params.extend([dept, cls])

        where_sql = " OR ".join(where_clauses)

        chunk_type_filter = ""
        if chunk_type:
            chunk_type_filter = "AND dc.chunk_type = %s"
            params.append(chunk_type)

        query_sql = f"""
            SELECT 
                dc.chunk_id::text,
                dc.content,
                dc.metadata,
                dc.chunk_type,
                dc.parent_chunk_id::text,
                d.filename,
                dept.department_name,
                d.classification,
                ts_rank_cd(dc.searchable_text_tsvector, websearch_to_tsquery('english', %s)) as rank
            FROM document_chunks dc
            JOIN documents d ON dc.doc_id = d.doc_id
            JOIN departments dept ON d.department_id = dept.department_id
            WHERE dc.searchable_text_tsvector @@ websearch_to_tsquery('english', %s)
              AND ({where_sql})
              {chunk_type_filter}
            ORDER BY rank DESC
            LIMIT %s
        """

        full_params = [query_text, query_text] + params + [k]

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query_sql, full_params)
                    rows = cur.fetchall()

            return [
                {
                    "chunk_id": row["chunk_id"],
                    "content": row["content"],
                    "metadata": {
                        **(row["metadata"] or {}),
                        "source": row["filename"],
                        "department": row["department_name"],
                        "classification": row["classification"],
                        "chunk_type": row["chunk_type"],
                    },
                    "parent_chunk_id": row["parent_chunk_id"],
                    "rank": float(row["rank"]),
                }
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Keyword search failed: {e}") from e

    def get_parent_chunk_content(self, parent_chunk_id: str) -> Optional[Dict]:
        """Retrieve parent chunk content by ID."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT dc.chunk_id::text, dc.content, dc.metadata, 
                           d.filename, dept.department_name, d.classification
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE dc.chunk_id = %s
                    """,
                    (parent_chunk_id,),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "chunk_id": row["chunk_id"],
                        "content": row["content"],
                        "metadata": {
                            **(row["metadata"] or {}),
                            "source": row["filename"],
                            "department": row["department_name"],
                            "classification": row["classification"],
                        },
                    }
                return None

    def get_chunks_by_ids(self, chunk_ids: List[str]) -> List[Dict]:
        """Retrieve multiple chunks by their IDs."""
        if not chunk_ids:
            return []

        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT dc.chunk_id::text, dc.content, dc.metadata, dc.chunk_type,
                           dc.parent_chunk_id::text, d.filename, 
                           dept.department_name, d.classification
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE dc.chunk_id = ANY(%s::uuid[])
                    """,
                    (chunk_ids,),
                )
                rows = cur.fetchall()

        return [
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "metadata": {
                    **(row["metadata"] or {}),
                    "source": row["filename"],
                    "department": row["department_name"],
                    "classification": row["classification"],
                    "chunk_type": row["chunk_type"],
                },
                "parent_chunk_id": row["parent_chunk_id"],
            }
            for row in rows
        ]

    # ────────────────────────────────────────────
    #      M2M Client Credentials Management
    # ────────────────────────────────────────────

    def create_m2m_client(
        self,
        client_name: str,
        client_secret_hash: str,
        owner_user_id: str,
        description: Optional[str] = None,
        service_account_user_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
    ) -> str:
        """Create a new M2M client for programmatic API access."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO m2m_clients 
                    (client_name, client_secret_hash, owner_user_id, description, 
                     service_account_user_id, scopes, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING client_id
                    """,
                    (
                        client_name,
                        client_secret_hash,
                        owner_user_id,
                        description,
                        service_account_user_id,
                        scopes,
                        expires_at,
                    ),
                )
                client_id = cur.fetchone()[0]
            conn.commit()
        return str(client_id)

    def get_m2m_client_by_id(self, client_id: str) -> Optional[Dict]:
        """Retrieve M2M client by client_id."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT client_id, client_name, client_secret_hash, description,
                           owner_user_id, service_account_user_id, is_active, scopes,
                           created_at, last_used_at, expires_at, metadata
                    FROM m2m_clients
                    WHERE client_id = %s
                    """,
                    (client_id,),
                )
                return cur.fetchone()

    def get_m2m_client_with_user_info(self, client_id: str) -> Optional[Dict]:
        """
        Retrieve M2M client with associated user/service account information.
        Returns user_id, email, role, department for authorization.
        """
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT 
                        m.client_id, m.client_name, m.client_secret_hash, m.is_active,
                        m.scopes, m.expires_at,
                        COALESCE(sa.user_id, owner.user_id) as user_id,
                        COALESCE(sa.email, owner.email) as email,
                        COALESCE(sa.department_id, owner.department_id) as department_id,
                        COALESCE(sa.role_id, owner.role_id) as role_id,
                        d.department_name, r.role_name
                    FROM m2m_clients m
                    LEFT JOIN users sa ON m.service_account_user_id = sa.user_id
                    LEFT JOIN users owner ON m.owner_user_id = owner.user_id
                    LEFT JOIN departments d ON COALESCE(sa.department_id, owner.department_id) = d.department_id
                    LEFT JOIN roles r ON COALESCE(sa.role_id, owner.role_id) = r.role_id
                    WHERE m.client_id = %s
                    LIMIT 1
                    """,
                    (client_id,),
                )
                return cur.fetchone()

    def update_m2m_client_last_used(self, client_id: str):
        """Update the last_used_at timestamp for a client."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE m2m_clients
                    SET last_used_at = CURRENT_TIMESTAMP
                    WHERE client_id = %s
                    """,
                    (client_id,),
                )
            conn.commit()

    def list_m2m_clients_by_owner(self, owner_user_id: str) -> List[Dict]:
        """List all M2M clients created by a specific owner."""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT client_id, client_name, description, is_active, scopes,
                           created_at, last_used_at, expires_at
                    FROM m2m_clients
                    WHERE owner_user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (owner_user_id,),
                )
                return cur.fetchall()

    def revoke_m2m_client(self, client_id: str, owner_user_id: str) -> bool:
        """Revoke (deactivate) an M2M client. Returns True if successful."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE m2m_clients
                    SET is_active = FALSE
                    WHERE client_id = %s AND owner_user_id = %s
                    RETURNING client_id
                    """,
                    (client_id, owner_user_id),
                )
                result = cur.fetchone()
            conn.commit()
        return result is not None

    def delete_m2m_client(self, client_id: str, owner_user_id: str) -> bool:
        """Permanently delete an M2M client. Returns True if successful."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM m2m_clients
                    WHERE client_id = %s AND owner_user_id = %s
                    RETURNING client_id
                    """,
                    (client_id, owner_user_id),
                )
                result = cur.fetchone()
            conn.commit()
        return result is not None

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
