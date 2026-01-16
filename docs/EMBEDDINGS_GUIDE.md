<div align="center">

# Embedding Model Configuration Guide

</div>

<br>

## Overview

The Sentinel RAG system implements a **Provider-Agnostic Embedding Architecture**. This design allows the application to switch between different embedding model providers (e.g., OpenAI, Google Gemini) without requiring code changes.

The system uses a **Factory Pattern** to instantiate the appropriate embedding driver based on configuration. This ensures that the core business logic remains decoupled from specific vendor implementations, promoting maintainability and future extensibility.

## Supported Providers

| Provider | Key Identifier | Description |
|----------|---------------|-------------|
| **OpenAI** | `openai` | Uses OpenAI's `text-embedding-3` series or legacy models. |
| **Google Gemini** | `gemini` | Uses Google's `models/embedding-001` or newer. |
| **Fake** | `fake` | Deterministic mock embeddings for testing and development cost-savings. |

## Configuration

Configuration is managed primarily through Environment Variables defined in your `.env` file.

### Global Settings

| Variable | Required | Default | Description |
|----------|:--------:|:-------:|-------------|
| `EMBEDDING_PROVIDER` | Yes | `fake` | The provider to use. Options: `openai`, `gemini`, `fake`. |
| `EMBEDDING_MODEL_NAME`| No | *Provider Default* | Specific model version to use (e.g., `text-embedding-3-large`). |
| `EMBEDDING_API_KEY` | No | `None` | Optional override for the API key. Preferably use provider-specific keys below. |

---

### Provider-Specific Configuration

#### 1. OpenAI (`openai`)

To use OpenAI embeddings, ensure you have an active API key from the [OpenAI Platform](https://platform.openai.com/).

**.env configuration:**
```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_API_KEY=your-key-here...

# Optional: Override default model (text-embedding-3-small)
EMBEDDING_MODEL_NAME=text-embedding-3-large
```

#### 2. Google Gemini (`gemini`)

To use Google's Generative AI embeddings, obtain an API key from [Google AI Studio](https://aistudio.google.com/).

**.env configuration:**
```bash
EMBEDDING_PROVIDER=gemini
EMBEDDING_API_KEY=your-key-here...

# Optional: Override default model (models/embedding-001)
EMBEDDING_MODEL_NAME=models/embedding-001
```

#### 3. Fake / Development (`fake`)

Default mode. Generates random but constant vectors for verifying pipeline flow without incurring API costs.

**.env configuration:**
```bash
EMBEDDING_PROVIDER=fake
```

## Adding New Providers

The system follows the **Open/Closed Principle**. To add support for a new provider (e.g., HuggingFace, Azure, Bedrock):

1.  **Update Dependencies**: Add the relevant LangChain integration package (e.g., `langchain-huggingface`) to `pyproject.toml`.
2.  **Update Factory**: Modify `src/sentinel_rag/core/embeddings.py` to include a new condition in the `EmbeddingFactory`.
3.  **Configure**: Add the new provider case and its specific initialization parameters.

Example extension logic:
```python
elif provider == "azure":
    return AzureOpenAIEmbeddings(
        azure_deployment=settings.embeddings.model_name,
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )
```
