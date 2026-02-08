<div align="center">
<img width="3000" height="607" alt="header_banner" src="https://github.com/user-attachments/assets/512c3c51-8ba3-41d1-a23b-915c42ad284c" />

<br>
<br>

**Sentinel RAG** is an RAG framework designed with "Security-First" philosophy. It solves the critical gap in standard RAG implementations: **lack of document-level permissions and data privacy.**

*The "Security-First" RAG Framework for Modern Enterprises*

![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)
![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)
![Pydantic v2](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=Pydantic&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white)

[Key Features](#-key-features) • [Getting Started](#-getting-started)

</div>

---

## 🎯 The Challenge

**The "Intern vs. CEO" Problem**

Most RAG implementations treat your knowledge base as a flat file system. When an LLM retrieves context, it doesn't know—or care—who is asking. This leads to critical data leaks: **an intern's query shouldn't trigger the retrieval of the CEO’s payroll data.**

**Sentinel RAG** acts as a secure proxy between your users and your data. It ensures that your AI only "knows" what the specific user is authorized to see, while stripping sensitive PII before it ever hits the inference engine.


## ✨ Key Features

- ⚖️ **Contextual Role-Based Access Control(RBAC):** Sentinel RAG injects **dynamic metadata filters** into the retrieval process. It matches the user's Role & Permission against document-level permissions in real-time.

- 🛡️ **Automated PII Sanitization:** Built-in middleware automatically detects and masks sensitive entities before context is sent to the LLM.

- 🔐 **Enterprise-Ready Authentication** Single-tenant OIDC authentication with JWT-based authorization, supporting both cookie (browser) and Bearer token (API) authentication methods.

- 📝 **Immutable Compliance Logging:** Every request is audited. Sentinel RAG logs the user identity, the specific document chunks retrieved, and the sanitized prompt, providing a full trail for GDPR, HIPAA, and SOC2 compliance.

- 🎯 **Industrial-Grade Rag Precision:** From advanced embeddings (_docs-to-markdown_ and _Context-Aware Hierarchical Splitting_) to _hybrid retrieval(vector + keyword)_ ensure precise context retrieval.


## 📸 App Screenshorts

<img width="1855" height="1093" alt="application_screenshort_1" src="https://github.com/user-attachments/assets/27f5d620-c497-476f-899a-41f9af089563" />
<img width="1861" height="1093" alt="application_screenshort_2" src="https://github.com/user-attachments/assets/4d113585-aba4-4147-8a5d-0fe6977b4fec" />

> These are the screenshots of the Steamlit Demo App


## 🚀 Getting Started

Sentinel RAG offers two setup options: **Docker** (recommended for quick setup) or **local installation** with `uv`.

### Using Docker (Recommended)

The fastest way to get Sentinel RAG running with all dependencies pre-configured.

#### 1. Clone, Config & Launch

```bash
# Clone the repository
git clone https://github.com/RajeshTechForge/sentinel-rag.git
cd sentinel-rag

# Create a `.env` file based on example
cp .env.example .env

# Build and start all services (PostgreSQL, Qdrant, API)
docker compose up --build
```

> This starts:
> - **Sentinel RAG API** on port `8000`
> - **PostgreSQL** on port `5432`
> - **Qdrant** on port `6333` (Dashboard: `http://localhost:6333/dashboard`)

### Local Setup

For local development without Docker. Requires external PostgreSQL and Qdrant instances.

#### 1. Prerequisites

Ensure you have:
- **PostgreSQL** 16+ running locally
- **Qdrant** running locally (via Docker)

```bash
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant

```

#### 2. Installation

```bash
# Clone the repository
git clone https://github.com/RajeshTechForge/sentinel-rag.git
cd sentinel-rag

# Install dependencies and create environment
uv sync
# Install in editable mode
uv pip install -e .
```

#### 3. Configuration

Create a `.env` file based on the example:

```bash
cp .env.example .env
```

> [!NOTE]
> For detailed configuration options, refer to the [CONFIGURATION Guide](docs/CONFIGURATION.md).

#### 4. Launch the API

```bash
uv run uvicorn sentinel_rag.api.app:app --reload
```

#### 5. Verify Setup

Check that all services are running:

```bash
# Test API health
curl http://localhost:8000/health

# Access Qdrant Dashboard
open http://localhost:6333/dashboard
```


## 🛠️ Tech Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.10 - 3.13 |
| **API Framework** | FastAPI (Async) |
| **Data Validation** | Pydantic v2 |
| **Package Manager** | uv |
| **Vector Search** | Qdrant |
| **Relational DB** | PostgreSQL |
| **Orchestration** | Docker & Docker Compose |


## 📚 Documentations

- [API Guide](docs/API_GUIDE.md)
- [CONFIGURATION Guide](docs/CONFIGURATION.md)
- [COMPLIANCE Guide](docs/COMPLIANCE.md)
- [DATABASE SEPARATION Guide](docs/DATABASE_SEPARATION.md)
- [EMBEDDINGS Guide](docs/EMBEDDINGS_GUIDE.md)
- [CONTRIBUTING Guidelines](CONTRIBUTING.md)


## 🤝 Contributing

We love contributors! Whether you are fixing a bug or suggesting a feature.  
Check out [Contributing Guidelines](CONTRIBUTING.md) for more details.


## 📄 License

Distributed under the **Apache License 2.0**. See [LICENSE](LICENSE.md) for more information.

---

<div align="center">
<p>Built with ❤️ for a more secure AI future by @RajeshTechForge</p>
</div>
