# Sentinel RAG - Streamlit Interface

## Quick Start

Run from project root:

```bash
# Linux/Mac
./app/run_streamlit.sh

# Windows
app\run_streamlit.bat
```

Or using uv directly:
```bash
uv run streamlit run app/streamlit_app.py
```

### Access the Application

Open your browser: **http://localhost:8501**


## Configuration

- **Streamlit**: `app/.streamlit/config.toml` (theme, port)
- **Database**: `.env` file in project root
- **RBAC**: `config/config.json`

> [!NOTE]
> Authentication is bypassed for demo purposes. Select users from the sidebar dropdown.


## Troubleshooting

**Database connection error:**
```bash
docker-compose up -d postgres
```

**Missing dependencies:**
```bash
uv sync --group dev
```

**Port already in use:**
```bash
uv run streamlit run app/streamlit_app.py --server.port 8502
```
