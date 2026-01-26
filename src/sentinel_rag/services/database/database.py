"""
DatabaseManager: Manages PostgreSQL database interactions for user, department, role, and document management,
including hierarchical document storage and hybrid retrieval using vector and keyword search.

"""

from contextlib import contextmanager
from os import path as os_path
from typing import List, Optional, Dict

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json, execute_batch
from pgvector.psycopg2 import register_vector
from langchain_core.documents import Document

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
            register_vector(conn)
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

        # Use raw connection to avoid register_vector error before extension exists
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

    #        User Management
    # -------------------------------
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
                    SELECT d.doc_id, d.filename, d.title, d.description, d.classification, d.created_at, dept.department_name
                    FROM documents d
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE d.uploaded_by = %s
                    ORDER BY d.created_at DESC
                """,
                    (user_id,),
                )
                return cur.fetchall()

    #       Department Management
    # -------------------------------
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

    #        Role Management
    # -------------------------------
    def create_role(self, role_name: str, department_name: str) -> str:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Get department_id
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
                    "SELECT r.role_name, d.department_name FROM roles r JOIN departments d ON r.department_id = d.department_id"
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
                    "INSERT INTO user_access (user_id, department_id, role_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, department_id, role_id),
                )
            conn.commit()

    #      General Document Management
    # -------------------------------------
    def save_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]],
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        classification: str,
    ) -> str:
        """
        Save document chunks with embeddings.
        Assumes all documents in the list belong to the same source file.
        If user_id is provided, creates a new document entry.
        """
        if not documents:
            return ""

        if len(documents) != len(embeddings):
            raise ValueError("Number of documents and embeddings must match")

        # Assume all chunks belong to the same source
        source = documents[0].metadata.get("source", "unknown")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (filename, title, description, uploaded_by, department_id, classification, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id
                    """,
                    (
                        source,
                        title,
                        description,
                        user_id,
                        department_id,
                        classification,
                        Json({"source": source}),
                    ),
                )
                doc_id = cur.fetchone()[0]

                # Batch insert chunks for efficiency
                insert_sql = """
                    INSERT INTO document_chunks (doc_id, content, page_number, chunk_index, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                chunk_data = [
                    (
                        doc_id,
                        doc.page_content,
                        doc.metadata.get("page", 0),
                        idx,
                        emb,
                        Json(doc.metadata),
                    )
                    for idx, (doc, emb) in enumerate(zip(documents, embeddings))
                ]
                execute_batch(cur, insert_sql, chunk_data, page_size=100)

            conn.commit()

        return str(doc_id)

    #     Parent-Document Document Upload
    # -------------------------------------------
    def save_hierarchical_documents(
        self,
        parent_chunks: List[Document],
        child_chunks: List[Document],
        child_embeddings: List[List[float]],
        relationships: List[tuple],
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        classification: str,
    ) -> str:
        """
        Save hierarchical document chunks for Parent-Document Retrieval.

        Args:
            parent_chunks: Larger chunks for context retrieval
            child_chunks: Smaller chunks for precise semantic search
            child_embeddings: Embeddings for child chunks only
            relationships: List of (parent_idx, child_idx) tuples

        Returns:
            doc_id: UUID of the created document
        """
        if not parent_chunks or not child_chunks:
            return ""

        if len(child_chunks) != len(child_embeddings):
            raise ValueError("Number of child chunks and embeddings must match")

        source = parent_chunks[0].metadata.get("source", "unknown")

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Create document entry
                cur.execute(
                    """
                    INSERT INTO documents (filename, title, description, uploaded_by, department_id, classification, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING doc_id
                    """,
                    (
                        source,
                        title,
                        description,
                        user_id,
                        department_id,
                        classification,
                        Json(
                            {"source": source, "retrieval_strategy": "parent_document"}
                        ),
                    ),
                )
                doc_id = cur.fetchone()[0]

                # Batch insert parent chunks
                parent_insert_sql = """
                    INSERT INTO document_chunks 
                    (doc_id, content, page_number, chunk_index, is_parent, chunk_type, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING chunk_id
                """
                parent_chunk_ids = []
                for idx, parent_doc in enumerate(parent_chunks):
                    cur.execute(
                        parent_insert_sql,
                        (
                            doc_id,
                            parent_doc.page_content,
                            parent_doc.metadata.get("page", 0),
                            idx,
                            True,
                            "parent",
                            Json(parent_doc.metadata),
                        ),
                    )
                    parent_chunk_ids.append(cur.fetchone()[0])

                # Batch insert child chunks
                child_insert_sql = """
                    INSERT INTO document_chunks 
                    (doc_id, content, page_number, chunk_index, embedding, parent_chunk_id, is_parent, chunk_type, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                child_data = []
                for idx, (child_doc, emb) in enumerate(
                    zip(child_chunks, child_embeddings)
                ):
                    parent_idx = child_doc.metadata.get("parent_index", 0)
                    parent_chunk_id = (
                        parent_chunk_ids[parent_idx]
                        if parent_idx < len(parent_chunk_ids)
                        else None
                    )
                    child_data.append(
                        (
                            doc_id,
                            child_doc.page_content,
                            child_doc.metadata.get("page", 0),
                            idx,
                            emb,
                            parent_chunk_id,
                            False,
                            "child",
                            Json(child_doc.metadata),
                        )
                    )
                execute_batch(cur, child_insert_sql, child_data, page_size=100)

            conn.commit()

        return str(doc_id)

    #      Hybrid Documents Retrieval
    # --------------------------------------
    def search_documents(
        self,
        query_text: str,
        query_embedding: List[float],
        filters: List[tuple],
        k: int = 0,
        threshold: float = 0,
        rrf_k: int = 60,
        use_parent_retrieval: bool = False,
    ) -> List[Document]:
        if not filters:
            print("No access filters provided. Access denied.")
            return []

        where_clauses = []
        params = []

        for dept, cls in filters:
            where_clauses.append(
                "(dept.department_name = %s AND d.classification = %s)"
            )
            params.extend([dept, cls])

        where_sql = " OR ".join(where_clauses)

        if use_parent_retrieval:
            query_sql = f"""
                WITH vector_search AS (
                    SELECT dc.chunk_id, ROW_NUMBER() OVER (ORDER BY dc.embedding <=> %s::vector) as rank
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE ({where_sql})
                      AND dc.chunk_type = 'child'
                      AND dc.embedding IS NOT NULL
                      AND (dc.embedding <=> %s::vector) < %s
                    ORDER BY dc.embedding <=> %s::vector
                    LIMIT %s
                ),
                keyword_search AS (
                    SELECT dc.chunk_id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.searchable_text_tsvector, websearch_to_tsquery('english', %s)) DESC) as rank
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE dc.searchable_text_tsvector @@ websearch_to_tsquery('english', %s)
                      AND ({where_sql})
                      AND dc.chunk_type = 'child'
                    ORDER BY rank
                    LIMIT %s
                ),
                matched_children AS (
                    SELECT DISTINCT
                        dc.chunk_id,
                        dc.parent_chunk_id,
                        COALESCE(1.0 / ({rrf_k} + vs.rank), 0.0) + 
                        COALESCE(1.0 / ({rrf_k} + ks.rank), 0.0) AS rrf_score
                    FROM document_chunks dc
                    LEFT JOIN vector_search vs ON dc.chunk_id = vs.chunk_id
                    LEFT JOIN keyword_search ks ON dc.chunk_id = ks.chunk_id
                    WHERE vs.chunk_id IS NOT NULL OR ks.chunk_id IS NOT NULL
                )
                SELECT DISTINCT ON (parent_dc.chunk_id)
                    parent_dc.content, 
                    parent_dc.metadata,
                    d.filename,
                    dept.department_name as department,
                    d.classification,
                    MAX(mc.rrf_score) as rrf_score
                FROM matched_children mc
                JOIN document_chunks parent_dc ON mc.parent_chunk_id = parent_dc.chunk_id
                JOIN documents d ON parent_dc.doc_id = d.doc_id
                JOIN departments dept ON d.department_id = dept.department_id
                GROUP BY parent_dc.chunk_id, parent_dc.content, parent_dc.metadata, 
                         d.filename, dept.department_name, d.classification
                ORDER BY parent_dc.chunk_id, MAX(mc.rrf_score) DESC
                LIMIT %s;
            """

            full_params = (
                [query_embedding]
                + params
                + [query_embedding, 1 - threshold, query_embedding, k + 10]
                + [query_text, query_text]
                + params
                + [k + 10]
                + [k]
            )
        else:
            query_sql = f"""
                WITH vector_search AS (
                    SELECT dc.chunk_id, ROW_NUMBER() OVER (ORDER BY dc.embedding <=> %s::vector) as rank
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE ({where_sql})
                      AND (dc.embedding <=> %s::vector) < %s
                    ORDER BY dc.embedding <=> %s::vector
                    LIMIT %s
                ),
                keyword_search AS (
                    SELECT dc.chunk_id, ROW_NUMBER() OVER (ORDER BY ts_rank_cd(dc.searchable_text_tsvector, websearch_to_tsquery('english', %s)) DESC) as rank
                    FROM document_chunks dc
                    JOIN documents d ON dc.doc_id = d.doc_id
                    JOIN departments dept ON d.department_id = dept.department_id
                    WHERE dc.searchable_text_tsvector @@ websearch_to_tsquery('english', %s)
                      AND ({where_sql})
                    ORDER BY rank
                    LIMIT %s
                )
                SELECT 
                    dc.content, 
                    dc.metadata,
                    d.filename,
                    dept.department_name as department,
                    d.classification,
                    COALESCE(1.0 / ({rrf_k} + vs.rank), 0.0) + 
                    COALESCE(1.0 / ({rrf_k} + ks.rank), 0.0) AS rrf_score
                FROM document_chunks dc
                LEFT JOIN vector_search vs ON dc.chunk_id = vs.chunk_id
                LEFT JOIN keyword_search ks ON dc.chunk_id = ks.chunk_id
                JOIN documents d ON dc.doc_id = d.doc_id
                JOIN departments dept ON d.department_id = dept.department_id
                WHERE vs.chunk_id IS NOT NULL OR ks.chunk_id IS NOT NULL
                ORDER BY rrf_score DESC
                LIMIT %s;
            """

            full_params = (
                [query_embedding]
                + params
                + [query_embedding, 1 - threshold, query_embedding, k + 10]
                + [query_text, query_text]
                + params
                + [k + 10]
                + [k]
            )

        results = []
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query_sql, full_params)
                    rows = cur.fetchall()

                    if not rows:
                        return []

                    for row in rows:
                        metadata = {
                            **(row["metadata"] or {}),
                            "source": row["filename"],
                            "department": row["department"],
                            "classification": row["classification"],
                            "score": round(row["rrf_score"], 4),
                            "retrieval_type": "parent"
                            if use_parent_retrieval
                            else "direct",
                        }
                        results.append(
                            Document(page_content=row["content"], metadata=metadata)
                        )

        except Exception as e:
            raise DatabaseError(f"Search failed: {e}") from e

        return results

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
