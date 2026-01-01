<div align="center">
<img width="3000" height="607" alt="header_banner" src="https://github.com/user-attachments/assets/512c3c51-8ba3-41d1-a23b-915c42ad284c" />

<br>
<br>

**Sentinel RAG** is an enterprise-ready Retrieval-Augmented Generation (RAG) framework designed with a "Security-First" philosophy. It solves the critical gap in standard RAG implementations: **the lack of document-level permissions and data privacy.**

*The "Security-First" RAG Framework for Modern Enterprises*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?logo=postgresql&logoColor=white)
[![View My Profile](https://img.shields.io/badge/View-My_Profile-blue?logo=GitHub)](https://github.com/rajeshtechforge)

<p align="center">
  <a href="https://github.com/RajeshTechForge/sentinel-rag/stargazers">
    <img src="https://img.shields.io/badge/⭐%20Give%20a%20Star-Support%20the%20project-orange?style=for-the-badge" alt="Give a Star">
  </a>
</p>

[Key Features](https://www.google.com/search?q=%23-key-features) • [Architecture](https://www.google.com/search?q=%23-architecture) • [Getting Started](https://www.google.com/search?q=%23-getting-started) • [Roadmap](https://www.google.com/search?q=%23-roadmap)

</div>

---

## 🎯 The Challenge

**The "Intern vs. CEO" Problem**

Most RAG implementations treat your knowledge base as a flat file system. When an LLM retrieves context, it doesn't know—or care—who is asking. This leads to critical data leaks: **an intern's query shouldn't trigger the retrieval of the CEO’s payroll data.**

**Sentinel RAG** acts as a secure proxy between your users and your data. It ensures that your AI only "knows" what the specific user is authorized to see, while stripping sensitive PII before it ever hits the inference engine.


## ✨ Key Features

### 🔐 Contextual RBAC (Role-Based Access Control)

Unlike standard vector searches, Sentinel RAG injects **dynamic metadata filters** into the retrieval process. It matches the user's JWT/Session roles against document-level permissions in real-time.

### 🛡️ Automated PII Sanitization

Built-in middleware automatically detects and masks sensitive entities (SSNs, API Keys, Personal Emails) using high-performance regex and NER (Named Entity Recognition) models before context is sent to the LLM.

### 📝 Immutable Compliance Logging

Every request is audited. Sentinel RAG logs the user identity, the specific document chunks retrieved, and the sanitized prompt, providing a full trail for GDPR, HIPAA, and SOC2 compliance.

### ⚡ Performance-First Stack

* **FastAPI & Pydantic v2:** Fully asynchronous, type-safe API.
* **`uv` Powered:** Lightning-fast dependency management and reproducible environments.
* **Vector Agnostic:** Native support for `pgvector`, with Qdrant integration on the roadmap.


## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph Client ["🖥️ Client Layer"]
        User[👤 User / App]
    end

    subgraph Security_Gate ["🛡️ Sentinel Middleware"]
        Auth[🔑 Auth & Role Extractor]
        RBAC_Filter[⚖️ Dynamic Filter Generator]
        PII_Proc[🔏 PII Redaction: Post-Retrieval]
    end

    subgraph Knowledge_Base ["🗄️ Secure Vector Store"]
        VDB[(pgvector / Qdrant)]
    end

    subgraph Intelligence ["🤖 Inference Engine"]
        LLM[LLM: Local / Cloud]
    end

    %% Flow logic
    User -->|1. Authenticated Query| Auth
    Auth -->|2. Scoped Metadata| RBAC_Filter
    RBAC_Filter -->|3. Filtered Search| VDB
    VDB -->|4. Raw Context| PII_Proc
    Auth -.->|5. Original Query| PII_Proc
    PII_Proc -->|6. Clean Query + Context| LLM
    LLM -->|7. Sanitized Response| User

```


## 🚀 Getting Started

Sentinel RAG offers two setup options: **Docker** (recommended for quick setup) or **local installation** with `uv`.

### Using Docker (Recommended)

The fastest way to get Sentinel RAG running with all dependencies pre-configured.

#### 1. Clone & Launch

```bash
# Clone the repository
git clone https://github.com/RajeshTechForge/sentinel-rag.git
cd sentinel-rag

# Build and start all services
docker compose up --build
```

This command will:
- Start a **PostgreSQL** database with the `pgvector` extension on port `5433` (mapped to avoid local conflicts)
- Build and launch the **Sentinel RAG API** on port `8000`

#### 2. Verify Installation

```bash
# Health check
curl http://localhost:8000/health
```

#### 3. Custom Configuration (Optional)

To use a custom configuration file:

```bash
# Mount your config and lunch
docker compose up --build -e SENTINEL_CONFIG_PATH=/app/config/custom.json

```


### Local Setup

Sentinel RAG utilizes [uv](https://github.com/astral-sh/uv) for high-speed dependency resolution.

#### 1. Installation

```bash
# Clone the repository
git clone https://github.com/RajeshTechForge/sentinel-rag.git
cd sentinel-rag

# Install dependencies and create environment
uv sync
```

#### 2. Configuration

Create a `.env` file based on the example:

```bash
cp .env.example .env
```

> [!NOTE]
> Please check out [CONFIGURATION.md](docs/CONFIGURATION.md) for comprehensive guidelines on architecting a custom `config.json` tailored for your organization’s structure.

#### 3. Launch the API

```bash
uv run uvicorn sentinel_rag.api.app:app --reload
```
> **Full API documentation:** [OpenAPI Spec](http://localhost:8000/docs) (available when running)


## 🛠️ Tech Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.10+ |
| **API Framework** | FastAPI (Async) |
| **Data Validation** | Pydantic v2 |
| **Package Manager** | uv |
| **Vector Search** | pgvector (PostgreSQL) |
| **Orchestration** | Docker & Docker Compose |

> [!NOTE]
> The system currently utilizes LangChain's FakeEmbeddings for demonstration purposes.


## 🗺️ Roadmap

* [x] Initial RBAC Logic for `pgvector`
* [x] PII Redaction Middleware
* [ ] Qdrant Vector DB Support
* [ ] Support for LLMs calls
* [ ] Admin Dashboard for Audit Log Visualization
* [ ] Multi-modal RAG support (Images/PDFs)


## 🤝 Contributing

We love contributors! Whether you are fixing a bug or suggesting a feature.  
Check out [Contributing Guidelines](CONTRIBUTING.md) for more details.


## 📄 License

Distributed under the **Apache License 2.0**. See [LICENSE](LICENSE.md) for more information.

---

<div align="center">
<p>Built with ❤️ for a more secure AI future.</p>
</div>
