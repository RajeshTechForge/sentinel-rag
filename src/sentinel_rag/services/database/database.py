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
    #                User Management
    # ─────────────────────────────────────────────
    def create_user(self, email: str, full_name: str = None) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, full_name) VALUES (%s, %s) RETURNING user_id",
                    (email, full_name),
                )
                user_id = cur.fetchone()[0]
            conn.commit()
        return str(user_id)

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                return cur.fetchone()

    def get_user_role_and_department(self, user_id: str) -> List[tuple]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT d.department_name, r.role_name
                    FROM user_access ua
                    JOIN roles r ON ua.role_id = r.role_id
                    JOIN departments d ON ua.department_id = d.department_id
                    WHERE ua.user_id = %s
                    """,
                    (user_id,),
                )
                return cur.fetchall()

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

    def get_user_department(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT d.department_name 
                    FROM departments d 
                    JOIN user_access ua ON d.department_id = ua.department_id 
                    WHERE ua.user_id = %s
                    """,
                    (user_id,),
                )
                return [row[0] for row in cur.fetchall()]

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

    def assign_role(self, user_id: str, role_name: str, department_name: str):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT r.role_id, d.department_id FROM roles r 
                    JOIN departments d ON r.department_id = d.department_id
                    WHERE r.role_name = %s AND d.department_name = %s
                    """,
                    (role_name, department_name),
                )
                res = cur.fetchone()
                if not res:
                    raise ValueError(
                        f"Role {role_name} not found in department {department_name}"
                    )
                role_id, department_id = res

                cur.execute(
                    """
                    INSERT INTO user_access (user_id, department_id, role_id) 
                    VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
                    """,
                    (user_id, department_id, role_id),
                )
            conn.commit()

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

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
