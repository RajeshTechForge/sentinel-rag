import os
from typing import List
from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from .exceptions import DocumentLoaderError


def load_documents(data_dir: str) -> List[Document]:
    document = []

    # Handle single file
    ext = os.path.splitext(data_dir)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(data_dir)
        document.extend(loader.load())
    elif ext == ".txt":
        loader = TextLoader(data_dir)
        document.extend(loader.load())
    else:
        raise DocumentLoaderError(f"Unsupported file type: {ext}")

    print(f"Document Loading complete.")
    return document


def split_documents(
    documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[Document]:
    # Splits documents into smaller chunks.
    print("Splitting text...")

    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        texts = text_splitter.split_documents(documents)
        print(f"Created {len(texts)} text chunks.")
        return texts

    except Exception as e:
        raise DocumentLoaderError(f"Failed to split documents: {e}")
