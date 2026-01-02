import os
import tempfile
import shutil
from importlib import resources
from langchain_community.embeddings import FakeEmbeddings

from .seeder import seed_initial_data
from .rbac_manager import RbacManager
from .pii_manager import PiiManager
from .document_processor import DocumentProcessor
from .exceptions import EngineError, DocumentIngestionError, QueryError


class SentinelEngine:
    def __init__(self, db=None, config_file: str = None):
        if config_file:
            self.config_file = config_file
        else:
            try:
                self.config_file = str(
                    resources.files("sentinel_rag.config").joinpath("default.json")
                )
                print("Warning: No config file provided. Using default config.")
            except Exception as e:
                raise EngineError(f"Failed to load default config file: {e}")

        self.db = db
        seed_initial_data(db=self.db, config_file=self.config_file)
        self.rbac = RbacManager(self.config_file)
        self.pii_manager = PiiManager()
        self.pii_manager.warm_up()
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

        doc_chunks = self.doc_processor.markdown_to_chunks(doc_content)
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
            raise DocumentIngestionError(f"Failed to save documents to database: {e}")

    def query(self, question: str, user_id: str, k: int = 5):
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
            results = self.db.search_documents(query_embedding, filters, k=k)

            if results:
                results = self.pii_manager.reduce_pii_documents(results)

            return results
        except Exception as e:
            raise QueryError(f"Failed to execute query: {e}")

    def close(self):
        """Cleanup resources."""
        if hasattr(self, "pii_manager"):
            self.pii_manager.close()
