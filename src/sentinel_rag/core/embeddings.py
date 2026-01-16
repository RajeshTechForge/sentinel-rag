"""
Embedding Factory Module

This module defines a factory class for creating embedding model instances
based on configuration settings. It supports multiple providers and adheres to
the 'Open/Closed' principle for easy extensibility."""

import os
from langchain_core.embeddings import Embeddings
from langchain_community.embeddings import FakeEmbeddings
from sentinel_rag.config.config import AppSettings


class EmbeddingFactory:
    @staticmethod
    def get_embedding_model(settings: AppSettings) -> Embeddings:
        provider = settings.embeddings.provider.lower()
        model_name = settings.embeddings.model_name
        api_key = settings.embeddings.api_key

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings

            target_model = model_name if model_name else "text-embedding-3-small"
            openai_key = api_key if api_key else os.getenv("OPENAI_API_KEY")

            return OpenAIEmbeddings(model=target_model, api_key=openai_key)

        elif provider == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            target_model = model_name if model_name else "models/embedding-001"
            google_key = api_key if api_key else os.getenv("GOOGLE_API_KEY")

            return GoogleGenerativeAIEmbeddings(
                model=target_model, google_api_key=google_key
            )

        elif provider == "fake":
            return FakeEmbeddings(size=1536)

        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
