import os
import tempfile
import shutil
from typing import Dict
from langchain_community.embeddings import FakeEmbeddings

from .seeder import seed_initial_data
from .rbac_manager import RbacManager
from .pii_manager import PiiManager
from .document_processor import DocumentProcessor
from .exceptions import DocumentIngestionError, QueryError


class SentinelEngine:
    def __init__(self, db=None, rbac_config: Dict = {}):
        self.db = db
        seed_initial_data(db=self.db, rbac_config=rbac_config)
        self.rbac = RbacManager(rbac_config)
        self.pii_manager = PiiManager()
        # self.pii_manager.warm_up()
        self.doc_processor = DocumentProcessor()
        self.embeddings = FakeEmbeddings(size=1536)

    def ingest_documents(
        self,
        source,
        title: str,
        description: str,
        user_id: str,
        department_id: str,
        classification: str,
        use_hierarchical: bool = False,
    ):
        """Uploads documents from path or UploadFile, splits them, generates embeddings and stores in DB."""

        doc_content = []
        tmp_path = None

        try:
            if isinstance(source, str):
                doc_content = self.doc_processor.smart_doc_parser(source)

            elif hasattr(source, "filename") and hasattr(source, "file"):
                # Handle UploadFile-like object
                suffix = os.path.splitext(source.filename)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    shutil.copyfileobj(source.file, tmp)
                    tmp_path = tmp.name
                doc_content = self.doc_processor.smart_doc_parser(tmp_path)
                # Update metadata to use original filename
                for doc in doc_content:
                    doc.metadata["source"] = source.filename

            else:
                raise DocumentIngestionError(
                    "Invalid source type provided. Expected file path or UploadFile object."
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

        # Choose chunking strategy
        if use_hierarchical:
            # Use Parent-Document Retrieval with hierarchical chunks
            chunk_data = self.doc_processor.create_context_aware_hierarchical_chunks(
                doc_content
            )
            parent_chunks = chunk_data["parent_chunks"]
            child_chunks = chunk_data["child_chunks"]
            relationships = chunk_data["relationships"]

            if not child_chunks:
                raise DocumentIngestionError("No child chunks created from documents.")

            try:
                print("Generating embeddings for child chunks...")
                text_content = [doc.page_content for doc in child_chunks]
                embeddings = self.embeddings.embed_documents(text_content)
                # Ensure embedding is a list of standard floats to avoid numpy types
                embeddings = [[float(x) for x in emb] for emb in embeddings]

            except Exception as e:
                raise DocumentIngestionError(f"Failed to generate embeddings: {e}")

            try:
                print("Saving hierarchical chunks to database...")
                doc_id = self.db.save_hierarchical_documents(
                    parent_chunks,
                    child_chunks,
                    embeddings,
                    relationships,
                    title,
                    description,
                    user_id,
                    department_id,
                    classification,
                )
                print("Hierarchical ingestion complete.")
                return doc_id
            except Exception as e:
                raise DocumentIngestionError(
                    f"Failed to save hierarchical documents to database: {e}"
                )
        else:
            # Use traditional flat chunking
            doc_chunks = self.doc_processor.create_context_aware_chunks(doc_content)
            if not doc_chunks:
                raise DocumentIngestionError("No text chunks created from documents.")

            try:
                print("Generating embeddings...")
                text_content = [doc.page_content for doc in doc_chunks]
                embeddings = self.embeddings.embed_documents(text_content)
                # Ensure embedding is a list of standard floats to avoid numpy types
                embeddings = [[float(x) for x in emb] for emb in embeddings]

            except Exception as e:
                raise DocumentIngestionError(f"Failed to generate embeddings: {e}")

            try:
                print("Saving to database...")
                doc_id = self.db.save_documents(
                    doc_chunks,
                    embeddings,
                    title,
                    description,
                    user_id,
                    department_id,
                    classification,
                )
                print("Ingestion complete.")
                return doc_id
            except Exception as e:
                raise DocumentIngestionError(
                    f"Failed to save documents to database: {e}"
                )

    def query(
        self,
        question: str,
        user_id: str,
        k: int = 5,
        use_parent_retrieval: bool = False,
    ):
        try:
            filters = self.rbac.get_user_access_filters(user_id, self.db)
            if not filters:
                print("User has no access to any documents.")
                return []

            query_embedding = self.embeddings.embed_query(question)
            # Ensure query_embedding is a list of standard floats
            query_embedding = [float(x) for x in query_embedding]
        except Exception as e:
            raise QueryError(f"Failed to generate query embedding: {e}")

        try:
            # Pass 'question' (text) along with the embedding and parent retrieval flag
            results = self.db.search_documents(
                question,
                query_embedding,
                filters,
                k=k,
                use_parent_retrieval=use_parent_retrieval,
            )

            if results:
                results = self.pii_manager.reduce_pii_documents(results)

            return results
        except Exception as e:
            raise QueryError(f"Failed to execute query: {e}")

    def close(self):
        """Cleanup resources."""
        if hasattr(self, "pii_manager"):
            self.pii_manager.close()
