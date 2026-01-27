"""
SentinelEngine: Core module for document ingestion, processing, and hybrid retrieval.

Orchestrates document chunking, embedding generation, and storage across PostgreSQL and Qdrant.
Implements RBAC and PII management for secure enterprise RAG.
"""

import os
import tempfile
import shutil
from typing import Dict, List, Optional
from uuid import uuid4
from langchain_core.documents import Document

from sentinel_rag.config.config import get_settings
from sentinel_rag.services.vectorstore import QdrantStore

from .embeddings import EmbeddingFactory
from .seeder import seed_initial_data
from .rbac_manager import RbacManager
from .pii_manager import PiiManager
from .document_processor import DocumentProcessor
from .exceptions import DocumentIngestionError, QueryError


def _to_native_floats(embedding) -> List[float]:
    """Convert embedding to native Python floats (handles numpy arrays)."""
    if hasattr(embedding, "tolist"):
        return embedding.tolist()
    return [float(x) for x in embedding]


class SentinelEngine:
    def __init__(
        self,
        db=None,
        vector_store: Optional[QdrantStore] = None,
        rbac_config: Dict = None,
        max_retrieved_docs: int = 20,
        similarity_threshold: float = 0.4,
        rrf_constant: int = 60,
    ):
        self.db = db
        seed_initial_data(db=self.db, rbac_config=rbac_config or {})
        self.rbac = RbacManager(rbac_config or {})
        self.pii_manager = PiiManager()
        self.doc_processor = DocumentProcessor()

        settings = get_settings()

        if vector_store:
            self.vector_store = vector_store
        else:
            self.vector_store = QdrantStore(
                host=settings.qdrant.host,
                port=settings.qdrant.port,
                api_key=settings.qdrant.api_key or None,
                prefer_grpc=settings.qdrant.prefer_grpc,
                vector_size=settings.embeddings.vector_size,
            )

        self.embeddings = EmbeddingFactory.get_embedding_model(settings)
        self.max_retrieved_docs = max_retrieved_docs
        self.similarity_threshold = similarity_threshold
        self.rrf_constant = rrf_constant

    def ingest_documents(
        self,
        source,
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        classification: str,
        use_hierarchical: bool = None,
    ):
        """Uploads documents from path or UploadFile, splits them, generates embeddings and stores in DB."""

        doc_content = []
        tmp_path = None

        if use_hierarchical is None:
            settings = get_settings()
            use_hierarchical = settings.doc_retrieval.use_parent_retrieval

        try:
            if isinstance(source, str):
                doc_content = self.doc_processor.smart_doc_parser(source)
                filename = os.path.basename(source)

            elif hasattr(source, "filename") and hasattr(source, "file"):
                suffix = os.path.splitext(source.filename)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    shutil.copyfileobj(source.file, tmp)
                    tmp_path = tmp.name
                doc_content = self.doc_processor.smart_doc_parser(tmp_path)
                filename = source.filename
                for doc in doc_content:
                    doc.metadata["source"] = source.filename
            else:
                raise DocumentIngestionError(
                    "Invalid source type. Expected file path or UploadFile object."
                )
        except DocumentIngestionError:
            raise
        except Exception as e:
            raise DocumentIngestionError(f"Failed to load documents: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not doc_content:
            raise DocumentIngestionError("No documents found in the provided source.")

        department_name = self.db.get_department_name_by_id(department_id) or "unknown"

        if use_hierarchical:
            return self._ingest_hierarchical(
                doc_content,
                filename,
                title,
                description,
                user_id,
                department_id,
                department_name,
                classification,
            )
        else:
            return self._ingest_standard(
                doc_content,
                filename,
                title,
                description,
                user_id,
                department_id,
                department_name,
                classification,
            )

    def _ingest_standard(
        self,
        doc_content: List[Document],
        filename: str,
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        department_name: str,
        classification: str,
    ) -> str:
        """Standard chunking and ingestion."""
        chunks = self.doc_processor.create_context_aware_chunks(doc_content)
        if not chunks:
            raise DocumentIngestionError("No text chunks created from documents.")

        try:
            texts = [doc.page_content for doc in chunks]
            embeddings = self.embeddings.embed_documents(texts)
            embeddings = [_to_native_floats(emb) for emb in embeddings]
        except Exception as e:
            raise DocumentIngestionError(f"Failed to generate embeddings: {e}")

        try:
            # Create document in PostgreSQL
            doc_id = self.db.create_document(
                filename=filename,
                title=title,
                description=description,
                user_id=user_id,
                department_id=department_id,
                classification=classification,
                metadata={"source": filename},
            )

            # Generate chunk IDs and prepare data
            chunk_ids = [str(uuid4()) for _ in chunks]
            contents = [doc.page_content for doc in chunks]
            page_numbers = [doc.metadata.get("page", 0) for doc in chunks]
            chunk_indexes = list(range(len(chunks)))
            metadatas = [
                {**doc.metadata, "chunk_index": idx} for idx, doc in enumerate(chunks)
            ]

            # Save to PostgreSQL (for full-text search)
            self.db.save_chunks_batch(
                doc_id=doc_id,
                chunk_ids=chunk_ids,
                contents=contents,
                page_numbers=page_numbers,
                chunk_indexes=chunk_indexes,
                metadatas=metadatas,
            )

            # Save to Qdrant (for vector search)
            self.vector_store.upsert_chunks(
                doc_id=doc_id,
                chunk_ids=chunk_ids,
                contents=contents,
                embeddings=embeddings,
                metadatas=metadatas,
                department=department_name,
                classification=classification,
            )

            return doc_id
        except Exception as e:
            raise DocumentIngestionError(f"Failed to save documents: {e}")

    def _ingest_hierarchical(
        self,
        doc_content: List[Document],
        filename: str,
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        department_name: str,
        classification: str,
    ) -> str:
        """Hierarchical parent-document chunking and ingestion."""
        settings = get_settings()
        chunk_data = self.doc_processor.create_context_aware_hierarchical_chunks(
            doc_content,
            parent_chunk_size=settings.doc_retrieval.parent_chunk_size,
            parent_overlap=settings.doc_retrieval.parent_chunk_overlap,
            child_chunk_size=settings.doc_retrieval.child_chunk_size,
            child_overlap=settings.doc_retrieval.child_chunk_overlap,
        )
        parent_chunks = chunk_data["parent_chunks"]
        child_chunks = chunk_data["child_chunks"]

        if not child_chunks:
            raise DocumentIngestionError("No child chunks created from documents.")

        try:
            texts = [doc.page_content for doc in child_chunks]
            embeddings = self.embeddings.embed_documents(texts)
            embeddings = [_to_native_floats(emb) for emb in embeddings]
        except Exception as e:
            raise DocumentIngestionError(f"Failed to generate embeddings: {e}")

        try:
            # Create document in PostgreSQL
            doc_id = self.db.create_document(
                filename=filename,
                title=title,
                description=description,
                user_id=user_id,
                department_id=department_id,
                classification=classification,
                metadata={"source": filename, "retrieval_strategy": "parent_document"},
            )

            # Generate parent chunk IDs
            parent_ids = [str(uuid4()) for _ in parent_chunks]
            parent_contents = [doc.page_content for doc in parent_chunks]
            parent_page_numbers = [doc.metadata.get("page", 0) for doc in parent_chunks]
            parent_metadatas = [
                {**doc.metadata, "chunk_index": idx, "chunk_type": "parent"}
                for idx, doc in enumerate(parent_chunks)
            ]

            # Save parent chunks to PostgreSQL
            self.db.save_chunks_batch(
                doc_id=doc_id,
                chunk_ids=parent_ids,
                contents=parent_contents,
                page_numbers=parent_page_numbers,
                chunk_indexes=list(range(len(parent_chunks))),
                metadatas=parent_metadatas,
                chunk_types=["parent"] * len(parent_chunks),
            )

            # Save parent chunks to Qdrant (for retrieval)
            self.vector_store.upsert_parent_chunks(
                doc_id=doc_id,
                parent_ids=parent_ids,
                contents=parent_contents,
                metadatas=parent_metadatas,
                department=department_name,
                classification=classification,
            )

            # Generate child chunk IDs and map to parents
            child_ids = [str(uuid4()) for _ in child_chunks]
            child_contents = [doc.page_content for doc in child_chunks]
            child_page_numbers = [doc.metadata.get("page", 0) for doc in child_chunks]

            # Map children to parent IDs
            child_parent_ids = []
            child_metadatas = []
            for idx, child_doc in enumerate(child_chunks):
                parent_idx = child_doc.metadata.get("parent_index", 0)
                parent_id = (
                    parent_ids[parent_idx]
                    if parent_idx < len(parent_ids)
                    else parent_ids[0]
                )
                child_parent_ids.append(parent_id)
                child_metadatas.append(
                    {
                        **child_doc.metadata,
                        "chunk_index": idx,
                        "chunk_type": "child",
                    }
                )

            # Save child chunks to PostgreSQL
            self.db.save_chunks_batch(
                doc_id=doc_id,
                chunk_ids=child_ids,
                contents=child_contents,
                page_numbers=child_page_numbers,
                chunk_indexes=list(range(len(child_chunks))),
                metadatas=child_metadatas,
                chunk_types=["child"] * len(child_chunks),
                parent_chunk_ids=child_parent_ids,
            )

            # Save child chunks to Qdrant with parent references
            self.vector_store.upsert_child_chunks_with_parents(
                doc_id=doc_id,
                child_ids=child_ids,
                parent_ids=child_parent_ids,
                contents=child_contents,
                embeddings=embeddings,
                metadatas=child_metadatas,
                department=department_name,
                classification=classification,
            )

            return doc_id
        except Exception as e:
            raise DocumentIngestionError(f"Failed to save hierarchical documents: {e}")

    def query(
        self,
        question: str,
        user_id: str,
        use_parent_retrieval: bool = True,
    ) -> List[Document]:
        """
        Query documents using hybrid search (vector + keyword) with RRF fusion.

        Args:
            question: Query string.
            user_id: ID of querying user (for RBAC).
            use_parent_retrieval: Whether to return parent chunks for context.

        Returns:
            List of Document objects with content and metadata.
        """
        try:
            filters = self.rbac.get_user_access_filters(user_id, self.db)
            if not filters:
                return []

            query_embedding = self.embeddings.embed_query(question)
            query_embedding = _to_native_floats(query_embedding)
        except Exception as e:
            raise QueryError(f"Failed to prepare query: {e}")

        try:
            # Vector search via Qdrant
            if use_parent_retrieval:
                vector_results = self.vector_store.search_with_parent_retrieval(
                    query_embedding=query_embedding,
                    filters=filters,
                    k=self.max_retrieved_docs,
                    threshold=self.similarity_threshold,
                )
            else:
                vector_results = self.vector_store.search(
                    query_embedding=query_embedding,
                    filters=filters,
                    k=self.max_retrieved_docs,
                    threshold=self.similarity_threshold,
                )

            # Keyword search via PostgreSQL
            chunk_type = "child" if use_parent_retrieval else None
            keyword_results = self.db.keyword_search(
                query_text=question,
                filters=filters,
                k=self.max_retrieved_docs,
                chunk_type=chunk_type,
            )

            # Fuse results using Reciprocal Rank Fusion
            results = self._rrf_fusion(
                vector_results,
                keyword_results,
                use_parent_retrieval,
            )

            if results:
                results = self.pii_manager.reduce_pii_documents(results)

            return results[: self.max_retrieved_docs]

        except Exception as e:
            raise QueryError(f"Failed to execute query: {e}")

    def _rrf_fusion(
        self,
        vector_results: List[dict],
        keyword_results: List[dict],
        use_parent_retrieval: bool,
    ) -> List[Document]:
        """
        Fuse vector and keyword search results using Reciprocal Rank Fusion.

        For parent retrieval, if a child match has a parent, we return the parent content.
        """
        rrf_scores = {}

        # Score vector results
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result["chunk_id"]
            rrf_scores[chunk_id] = {
                "score": 1.0 / (self.rrf_constant + rank),
                "content": result["content"],
                "metadata": result["metadata"],
                "vector_score": result.get("score", 0),
            }

        # Score keyword results
        for rank, result in enumerate(keyword_results, start=1):
            chunk_id = result["chunk_id"]
            rrf_increment = 1.0 / (self.rrf_constant + rank)

            if chunk_id in rrf_scores:
                rrf_scores[chunk_id]["score"] += rrf_increment
            else:
                # For parent retrieval, fetch parent content if needed
                content = result["content"]
                metadata = result["metadata"]

                if use_parent_retrieval and result.get("parent_chunk_id"):
                    parent = self.db.get_parent_chunk_content(result["parent_chunk_id"])
                    if parent:
                        content = parent["content"]
                        metadata = {**metadata, **parent.get("metadata", {})}

                rrf_scores[chunk_id] = {
                    "score": rrf_increment,
                    "content": content,
                    "metadata": metadata,
                    "keyword_rank": result.get("rank", 0),
                }

        # Sort by RRF score and convert to Documents
        sorted_results = sorted(
            rrf_scores.values(),
            key=lambda x: x["score"],
            reverse=True,
        )

        documents = []
        seen_content = set()

        for item in sorted_results:
            content_hash = hash(item["content"][:500])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            metadata = {
                **item["metadata"],
                "score": round(item["score"], 4),
                "retrieval_type": "parent" if use_parent_retrieval else "direct",
            }
            documents.append(Document(page_content=item["content"], metadata=metadata))

        return documents

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document from both PostgreSQL and Qdrant."""
        try:
            self.vector_store.delete_by_doc_id(doc_id)
            return self.db.delete_document(doc_id)
        except Exception as e:
            raise DocumentIngestionError(f"Failed to delete document: {e}")

    def close(self):
        """Cleanup resources."""
        if hasattr(self, "pii_manager"):
            self.pii_manager.close()
        if hasattr(self, "vector_store"):
            self.vector_store.close()
