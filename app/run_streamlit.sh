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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. Please install Docker first."
    exit 1
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if ! pg_isready -h localhost -p 5432 &> /dev/null; then
        echo "⚠️  PostgreSQL doesn't appear to be running on localhost:5432"
        echo "If using Docker: docker-compose up -d postgres"
    fi
fi

# Check if Qdrant is running
echo "Checking Qdrant connection..."
QDRANT_CONTAINER="qdrant"
QDRANT_RUNNING=$(docker ps --filter "name=$QDRANT_CONTAINER" --filter "status=running" -q)

if [ -z "$QDRANT_RUNNING" ]; then
    echo "⚠️  Qdrant is not running. Starting Qdrant container..."
    
    # Check if container exists but is stopped
    QDRANT_EXISTS=$(docker ps -a --filter "name=$QDRANT_CONTAINER" -q)
    
    if [ -n "$QDRANT_EXISTS" ]; then
        echo "   Restarting existing Qdrant container..."
        docker start $QDRANT_CONTAINER
    else
        echo "   Creating new Qdrant container..."
        docker run -d --name $QDRANT_CONTAINER \
            -p 6333:6333 -p 6334:6334 \
            -v "$(pwd)/qdrant_data:/qdrant/storage" \
            qdrant/qdrant
    fi
    
    # Wait for Qdrant to be ready
    echo "   Waiting for Qdrant to start..."
    sleep 3
    
    # Verify Qdrant is running
    if curl -s http://localhost:6333/readyz > /dev/null 2>&1; then
        echo "✅ Qdrant is now running on port 6333"
    else
        echo "⚠️  Qdrant may not be fully ready. Please check manually."
    fi
else
    echo "✅ Qdrant is already running"
fi

echo ""
echo "🚀 Launching Streamlit Interface..."
echo "📍 Access at: http://localhost:8501"
echo "📊 Qdrant Dashboard: http://localhost:6333/dashboard"
echo ""

# Run streamlit using uv (automatically handles dependencies and virtual env)
uv run streamlit run app/streamlit_app.py
