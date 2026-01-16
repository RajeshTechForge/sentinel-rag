import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from sentinel_rag.config.config import AppSettings
from sentinel_rag.core.embeddings import EmbeddingFactory, FakeEmbeddings


# Mock imports for optional dependencies so tests don't crash if not installed
@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=AppSettings)
    settings.embeddings = MagicMock()
    return settings


def test_factory_returns_fake_embeddings_by_default(mock_settings):
    mock_settings.embeddings.provider = "fake"
    mock_settings.embeddings.model_name = ""
    mock_settings.embeddings.api_key = ""

    model = EmbeddingFactory.get_embedding_model(mock_settings)
    assert isinstance(model, FakeEmbeddings)


def test_factory_raises_value_error_for_unknown_provider(mock_settings):
    mock_settings.embeddings.provider = "unknown_provider"

    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        EmbeddingFactory.get_embedding_model(mock_settings)


@patch.dict(os.environ, {"OPENAI_API_KEY": "sk-12345"})
def test_factory_initializes_openai(mock_settings):
    mock_settings.embeddings.provider = "openai"
    mock_settings.embeddings.model_name = "text-embedding-3-large"
    mock_settings.embeddings.api_key = "test-key"

    # Mock the module and class to simulate successful import
    mock_module = MagicMock()
    mock_class = MagicMock()
    mock_module.OpenAIEmbeddings = mock_class

    with patch.dict(sys.modules, {"langchain_openai": mock_module}):
        EmbeddingFactory.get_embedding_model(mock_settings)

        mock_class.assert_called_once_with(
            model="text-embedding-3-large", api_key="test-key"
        )


@patch.dict(os.environ, {"GOOGLE_API_KEY": "google-key-123"})
def test_factory_initializes_gemini(mock_settings):
    mock_settings.embeddings.provider = "gemini"
    mock_settings.embeddings.model_name = ""
    mock_settings.embeddings.api_key = ""  # Should fallback to env

    # Mock the module and class to simulate successful import
    mock_module = MagicMock()
    mock_class = MagicMock()
    mock_module.GoogleGenerativeAIEmbeddings = mock_class

    with patch.dict(sys.modules, {"langchain_google_genai": mock_module}):
        EmbeddingFactory.get_embedding_model(mock_settings)

        mock_class.assert_called_once_with(
            model="models/embedding-001", google_api_key="google-key-123"
        )
