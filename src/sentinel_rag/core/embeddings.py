"""
Embedding Factory Module

Factory for creating embedding model instances based on configuration.
Supports multiple providers with lazy loading for optimal startup time.
"""

import os
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import FakeEmbeddings
from sentinel_rag.config.config import AppSettings

_DEFAULT_MODELS = {
    "openai": "text-embedding-3-small",
    "gemini": "models/embedding-001",
}


class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(settings: AppSettings) -> Embeddings:
        provider = settings.embeddings.provider.lower()
        model = settings.embeddings.model_name
        api_key = settings.embeddings.api_key

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=model or _DEFAULT_MODELS["openai"],
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
            )

        if provider == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            return GoogleGenerativeAIEmbeddings(
                model=model or _DEFAULT_MODELS["gemini"],
                google_api_key=api_key or os.getenv("GOOGLE_API_KEY"),
            )

        if provider == "fake":
            return FakeEmbeddings(size=1536)

        raise ValueError(f"Unsupported embedding provider: {provider}")
