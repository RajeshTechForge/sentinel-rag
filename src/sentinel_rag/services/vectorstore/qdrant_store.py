"""
Qdrant Vector Store Service.

Handles all vector storage and similarity search operations using Qdrant.
Integrates with PostgreSQL for hybrid search combining vector similarity
with full-text search results using Reciprocal Rank Fusion (RRF).
"""

from typing import List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from .exceptions import VectorStoreError, CollectionError, UpsertError, SearchError


COLLECTION_NAME = "document_chunks"
PARENT_COLLECTION_NAME = "parent_chunks"


class QdrantStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        prefer_grpc: bool = True,
        vector_size: int = 1536,
    ):
        self._host = host
        self._port = port
        self._api_key = api_key
        self._vector_size = vector_size

        try:
            self._client = QdrantClient(
                host=host,
                port=port,
                api_key=api_key,
                prefer_grpc=prefer_grpc,
            )
            self._ensure_collections()
        except Exception as e:
            raise VectorStoreError(f"Failed to connect to Qdrant: {e}") from e

    def _ensure_collections(self):
        """Create collections if they don't exist."""
        for collection_name in [COLLECTION_NAME, PARENT_COLLECTION_NAME]:
            try:
                self._client.get_collection(collection_name)
            except (UnexpectedResponse, Exception):
                self._create_collection(collection_name)

    def _create_collection(self, collection_name: str):
        """Create a collection with optimized settings."""
        try:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self._vector_size,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                ),
                hnsw_config=models.HnswConfigDiff(
                    m=16,
                    ef_construct=100,
                    on_disk=True,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    memmap_threshold=20000,
                    indexing_threshold=20000,
                ),
                on_disk_payload=True,
            )

            # Create payload indexes for filtered search
            for field in ["doc_id", "department", "classification", "chunk_type"]:
                self._client.create_payload_index(
                    collection_name=collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

        except Exception as e:
            raise CollectionError(
                f"Failed to create collection {collection_name}: {e}"
            ) from e

    def upsert_chunks(
        self,
        doc_id: str,
        chunk_ids: List[str],
        contents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        department: str,
        classification: str,
    ) -> int:
        """
        Upsert document chunks to Qdrant.

        Returns:
            Number of points upserted.
        """
        if not chunk_ids:
            return 0

        points = []
        for chunk_id, content, embedding, metadata in zip(
            chunk_ids, contents, embeddings, metadatas
        ):
            payload = {
                "doc_id": doc_id,
                "content": content,
                "department": department,
                "classification": classification,
                "chunk_type": metadata.get("chunk_type", "child"),
                "page_number": metadata.get("page", 0),
                "chunk_index": metadata.get("chunk_index", 0),
                **{
                    k: v
                    for k, v in metadata.items()
                    if k not in ("page", "chunk_index", "chunk_type")
                },
            }

            points.append(
                models.PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        try:
            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )
            return len(points)
        except Exception as e:
            raise UpsertError(f"Failed to upsert chunks: {e}") from e

    def upsert_parent_chunks(
        self,
        doc_id: str,
        parent_ids: List[str],
        contents: List[str],
        metadatas: List[dict],
        department: str,
        classification: str,
    ) -> int:
        """
        Store parent chunks (without embeddings) for parent-document retrieval.
        Uses a dummy zero vector since we only need to store content for retrieval.
        """
        if not parent_ids:
            return 0

        points = []
        dummy_vector = [0.0] * self._vector_size

        for parent_id, content, metadata in zip(parent_ids, contents, metadatas):
            payload = {
                "doc_id": doc_id,
                "content": content,
                "department": department,
                "classification": classification,
                "chunk_type": "parent",
                "page_number": metadata.get("page", 0),
                "chunk_index": metadata.get("chunk_index", 0),
                **{
                    k: v
                    for k, v in metadata.items()
                    if k not in ("page", "chunk_index", "chunk_type")
                },
            }

            points.append(
                models.PointStruct(
                    id=parent_id,
                    vector=dummy_vector,
                    payload=payload,
                )
            )

        try:
            self._client.upsert(
                collection_name=PARENT_COLLECTION_NAME,
                points=points,
                wait=True,
            )
            return len(points)
        except Exception as e:
            raise UpsertError(f"Failed to upsert parent chunks: {e}") from e

    def upsert_child_chunks_with_parents(
        self,
        doc_id: str,
        child_ids: List[str],
        parent_ids: List[str],
        contents: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict],
        department: str,
        classification: str,
    ) -> int:
        """
        Upsert child chunks with references to their parent chunks.
        """
        if not child_ids:
            return 0

        points = []
        for child_id, parent_id, content, embedding, metadata in zip(
            child_ids, parent_ids, contents, embeddings, metadatas
        ):
            payload = {
                "doc_id": doc_id,
                "content": content,
                "parent_chunk_id": parent_id,
                "department": department,
                "classification": classification,
                "chunk_type": "child",
                "page_number": metadata.get("page", 0),
                "chunk_index": metadata.get("chunk_index", 0),
                **{
                    k: v
                    for k, v in metadata.items()
                    if k not in ("page", "chunk_index", "chunk_type", "parent_index")
                },
            }

            points.append(
                models.PointStruct(
                    id=child_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        try:
            self._client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )
            return len(points)
        except Exception as e:
            raise UpsertError(f"Failed to upsert child chunks: {e}") from e

    def search(
        self,
        query_embedding: List[float],
        filters: List[tuple],
        k: int = 20,
        threshold: float = 0.4,
    ) -> List[dict]:
        """
        Search for similar chunks with RBAC filtering.

        Args:
            query_embedding: Query vector.
            filters: List of (department, classification) tuples the user can access.
            k: Number of results to return.
            threshold: Minimum similarity score (0-1, cosine similarity).

        Returns:
            List of dicts with chunk_id, content, metadata, and score.
        """
        if not filters:
            return []

        # Build filter conditions for RBAC
        should_conditions = [
            models.Filter(
                must=[
                    models.FieldCondition(
                        key="department",
                        match=models.MatchValue(value=dept),
                    ),
                    models.FieldCondition(
                        key="classification",
                        match=models.MatchValue(value=cls),
                    ),
                ]
            )
            for dept, cls in filters
        ]

        query_filter = models.Filter(should=should_conditions)

        try:
            response = self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                query_filter=query_filter,
                limit=k,
                score_threshold=threshold,
                with_payload=True,
            )

            return [
                {
                    "chunk_id": str(point.id),
                    "content": point.payload.get("content", ""),
                    "metadata": {
                        k: v for k, v in point.payload.items() if k != "content"
                    },
                    "score": point.score,
                }
                for point in response.points
            ]
        except Exception as e:
            raise SearchError(f"Vector search failed: {e}") from e

    def search_with_parent_retrieval(
        self,
        query_embedding: List[float],
        filters: List[tuple],
        k: int = 20,
        threshold: float = 0.4,
    ) -> List[dict]:
        """
        Search child chunks and return their parent chunks for broader context.

        Args:
            query_embedding: Query vector.
            filters: RBAC filters.
            k: Number of parent chunks to return.
            threshold: Minimum similarity score.

        Returns:
            List of parent chunk data with aggregated scores.
        """
        if not filters:
            return []

        # Build filter for child chunks only
        should_conditions = [
            models.Filter(
                must=[
                    models.FieldCondition(
                        key="department",
                        match=models.MatchValue(value=dept),
                    ),
                    models.FieldCondition(
                        key="classification",
                        match=models.MatchValue(value=cls),
                    ),
                    models.FieldCondition(
                        key="chunk_type",
                        match=models.MatchValue(value="child"),
                    ),
                ]
            )
            for dept, cls in filters
        ]

        query_filter = models.Filter(should=should_conditions)

        try:
            # Search more children to find diverse parents
            response = self._client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_embedding,
                query_filter=query_filter,
                limit=k * 3,
                score_threshold=threshold,
                with_payload=True,
            )

            if not response.points:
                return []

            # Group by parent and keep best score
            parent_scores = {}
            for point in response.points:
                parent_id = point.payload.get("parent_chunk_id")
                if parent_id:
                    if (
                        parent_id not in parent_scores
                        or point.score > parent_scores[parent_id]
                    ):
                        parent_scores[parent_id] = point.score

            if not parent_scores:
                return []

            # Fetch parent chunks by IDs
            parent_ids = list(parent_scores.keys())
            parent_points = self._client.retrieve(
                collection_name=PARENT_COLLECTION_NAME,
                ids=parent_ids,
                with_payload=True,
            )

            # Build results with parent content and child scores
            results = []
            for point in parent_points:
                parent_id = str(point.id)
                results.append(
                    {
                        "chunk_id": parent_id,
                        "content": point.payload.get("content", ""),
                        "metadata": {
                            k: v for k, v in point.payload.items() if k != "content"
                        },
                        "score": parent_scores.get(parent_id, 0.0),
                    }
                )

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:k]

        except Exception as e:
            raise SearchError(f"Parent retrieval search failed: {e}") from e

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks for a document."""
        deleted = 0
        for collection_name in [COLLECTION_NAME, PARENT_COLLECTION_NAME]:
            try:
                self._client.delete(
                    collection_name=collection_name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="doc_id",
                                    match=models.MatchValue(value=doc_id),
                                )
                            ]
                        )
                    ),
                    wait=True,
                )
                deleted += 1
            except Exception:
                pass
        return deleted

    def get_collection_info(self) -> dict:
        """Get information about the collections."""
        try:
            main_info = self._client.get_collection(COLLECTION_NAME)
            parent_info = self._client.get_collection(PARENT_COLLECTION_NAME)
            return {
                "main_collection": {
                    "name": COLLECTION_NAME,
                    "points_count": main_info.points_count,
                    "vectors_count": main_info.vectors_count,
                },
                "parent_collection": {
                    "name": PARENT_COLLECTION_NAME,
                    "points_count": parent_info.points_count,
                    "vectors_count": parent_info.vectors_count,
                },
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to get collection info: {e}") from e

    def close(self):
        """Close the Qdrant client connection."""
        if self._client:
            self._client.close()
            self._client = None


def generate_chunk_id() -> str:
    """Generate a UUID string for chunk identification."""
    return str(uuid4())
