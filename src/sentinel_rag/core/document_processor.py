import os
from typing import Optional
import pymupdf
import pymupdf.layout
import pymupdf4llm
from markitdown import MarkItDown
from docling.document_converter import DocumentConverter
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


from .exceptions import DocumentProcessorError


# Complexity thresholds
SIMPLE_THRESHOLD = 3
MODERATE_THRESHOLD = 7

# Scoring weights
SCAN_SCORE = 5
TABLE_COLUMN_SCORE = 3
DENSE_PAGE_SCORE = 2
UNTAGGED_SCORE = 1
COMPLEX_PRODUCER_SCORE = 2

# Detection thresholds
MIN_TEXT_LENGTH = 50
ALIGNMENT_DUPLICATES_THRESHOLD = 5
DENSE_BLOCK_THRESHOLD = 50


class DocumentProcessor:
    def __init__(self):
        self.docling_parser = DocumentConverter()
        self.markitdown_parser = MarkItDown()

    def pdf_complexity_score(
        self, doc: pymupdf.Document, sample_pages: int = 5
    ) -> float:
        score = 0
        pages_to_check = min(len(doc), sample_pages)

        # Tagged PDF Check
        try:
            catalog = doc.pdf_catalog()
            keys = doc.xref_get_keys(catalog) if catalog else []
            print(keys)
            if "StructTreeRoot" not in keys:
                score += UNTAGGED_SCORE
        except Exception:
            score += UNTAGGED_SCORE

        # Producer Analysis
        try:
            metadata = doc.metadata
            producer = metadata.get("producer", "").lower()
            creator = metadata.get("creator", "").lower()

            complex_tools = ["indesign", "latex", "tex"]
            simple_tools = ["microsoft word", "word"]

            if any(tool in producer or tool in creator for tool in complex_tools):
                score += COMPLEX_PRODUCER_SCORE
            elif any(tool in producer or tool in creator for tool in simple_tools):
                score = max(0, score - 1)
        except Exception:
            pass

        for i in range(pages_to_check):
            page = doc[i]
            blocks = page.get_text("blocks")
            images = page.get_images()

            # Image/Scan Detection
            if len(page.get_text().strip()) < MIN_TEXT_LENGTH and len(images) > 0:
                score += SCAN_SCORE

            # Table/Column Detection (Block Alignment)
            y_coords = [round(b[1], 1) for b in blocks]
            duplicates = len(y_coords) - len(set(y_coords))
            if duplicates > ALIGNMENT_DUPLICATES_THRESHOLD:
                score += TABLE_COLUMN_SCORE

            # Content Density
            if len(blocks) > DENSE_BLOCK_THRESHOLD:
                score += DENSE_PAGE_SCORE

        return score / pages_to_check if pages_to_check > 0 else 0

    #    Intelligent PDF Parsing
    # -------------------------------
    def pdf_parser(self, file_path: str) -> str:
        doc = None
        try:
            doc = pymupdf.open(file_path)
            score = self.pdf_complexity_score(doc)
        finally:
            if doc:
                doc.close()

        if score < MODERATE_THRESHOLD:
            return pymupdf4llm.to_markdown(file_path)
        else:
            result = self.docling_parser.convert(file_path)
            return result.document.export_to_markdown()

    #   Universal Smart Document Parser
    # ------------------------------------
    def smart_doc_parser(self, file_path: str) -> Optional[str]:
        if not os.path.exists(file_path):
            raise DocumentProcessorError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self.pdf_parser(file_path)
        elif ext in [".docx", ".pptx", ".xls", ".xlsx"]:
            result = self.markitdown_parser.convert(file_path)
            return result.text_content
        else:
            if ext in [".txt", ".md", ".markdown"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            raise DocumentProcessorError(f"Unsupported file format: {ext}")

    #   Context-Aware Chunking
    # ---------------------------
    def create_context_aware_chunks(
        self, markdown_text: str, chunk_size: int = 1000, chunk_overlap: int = 100
    ) -> list:
        # Define the headers need to split
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

        try:
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on, strip_headers=False
            )
            md_header_splits = markdown_splitter.split_text(markdown_text)
            recursive_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[
                    "\n\n\n",
                    "\n\n",
                    "\n",
                    ".",
                    " ",
                    "",
                ],  # Priority of split characters
            )
            final_chunks = recursive_splitter.split_documents(md_header_splits)
        except Exception as e:
            raise DocumentProcessorError(f"Error during markdown splitting: {e}")

        return final_chunks

    # Context-Aware Hierarchical chunking for Parent-Document Retrieval
    # -----------------------------------------------------------------
    def create_context_aware_hierarchical_chunks(
        self,
        markdown_text: str,
        parent_chunk_size: int = 2000,
        parent_overlap: int = 200,
        child_chunk_size: int = 400,
        child_overlap: int = 50,
    ) -> dict:
        """
        Create hierarchical chunks for Parent-Document Retrieval.

        Returns:
            dict: {
                'parent_chunks': List[Document],  # Larger chunks for context
                'child_chunks': List[Document],   # Smaller chunks for search
                'relationships': List[tuple]       # (parent_idx, child_idx) mappings
            }
        """
        # First, create larger parent chunks
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

        try:
            # Split by headers first
            markdown_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on, strip_headers=False
            )
            md_header_splits = markdown_splitter.split_text(markdown_text)

            # Create parent chunks (larger, for context)
            parent_splitter = RecursiveCharacterTextSplitter(
                chunk_size=parent_chunk_size,
                chunk_overlap=parent_overlap,
                separators=["\n\n\n", "\n\n", "\n", ".", " ", ""],
            )
            parent_chunks = parent_splitter.split_documents(md_header_splits)

            # Create child chunks from each parent (smaller, for precise search)
            child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=child_chunk_size,
                chunk_overlap=child_overlap,
                separators=["\n\n", "\n", ".", " ", ""],
            )

            all_child_chunks = []
            relationships = []  # (parent_idx, child_idx)

            for parent_idx, parent_chunk in enumerate(parent_chunks):
                # Split parent into children
                children = child_splitter.split_documents([parent_chunk])

                for child in children:
                    child_idx = len(all_child_chunks)
                    # Add parent reference to child metadata
                    child.metadata["parent_index"] = parent_idx
                    all_child_chunks.append(child)
                    relationships.append((parent_idx, child_idx))

                # Mark parent chunk metadata
                parent_chunk.metadata["is_parent"] = True
                parent_chunk.metadata["parent_index"] = parent_idx

            return {
                "parent_chunks": parent_chunks,
                "child_chunks": all_child_chunks,
                "relationships": relationships,
            }

        except Exception as e:
            raise DocumentProcessorError(f"Error during hierarchical chunking: {e}")
