#!/bin/bash

# Production startup script for AI Auditor
# This script handles initialization, health checks, and graceful startup

set -e

echo "🚀 Starting AI Auditor..."

# Set environment
export PYTHONUNBUFFERED=1
export ENVIRONMENT=${ENVIRONMENT:-production}

# Wait for dependencies
if [ "$USE_MILVUS" = "true" ]; then
    echo "⏳ Waiting for Milvus to be ready..."
    timeout=60
    elapsed=0
    until nc -z ${MILVUS_HOST:-localhost} ${MILVUS_PORT:-19530} || [ $elapsed -eq $timeout ]; do
        sleep 2
        elapsed=$((elapsed + 2))
        echo "  Still waiting... ($elapsed/$timeout seconds)"
    done
    
    if [ $elapsed -eq $timeout ]; then
        echo "❌ Timeout waiting for Milvus"
        exit 1
    fi
    echo "✅ Milvus is ready"
fi

# Run migrations or initialization if needed
if [ -f "/app/scripts/init.py" ]; then
    echo "🔧 Running initialization..."
    python /app/scripts/init.py
fi

# Start the application
echo "✅ All checks passed. Starting application..."
exec uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000} --workers ${MAX_WORKERS:-4}
