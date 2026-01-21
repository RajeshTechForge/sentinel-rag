#!/bin/bash

# Sentinel RAG Streamlit Launcher
# This script launches the Streamlit interface for Sentinel RAG

echo "🛡️  Starting Sentinel RAG Interface..."
echo "========================================="
echo ""

# Get the parent directory (project root)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Creating from .env.example..."
    cp .env.example .env
    echo "✅ Please update .env with your configuration"
    echo ""
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv not found. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "Using uv package manager..."

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if ! pg_isready -h localhost -p 5432 &> /dev/null; then
        echo "⚠️  PostgreSQL doesn't appear to be running on localhost:5432"
        echo "If using Docker: docker-compose up -d postgres"
    fi
fi

echo ""
echo "🚀 Launching Streamlit Interface..."
echo "📍 Access at: http://localhost:8501"
echo ""

# Run streamlit using uv (automatically handles dependencies and virtual env)
uv run streamlit run app/streamlit_app.py
