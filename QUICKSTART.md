# 🚀 Quick Start Guide - AI Auditor

## Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.10 or 3.11 installed
- ✅ Poetry installed (or pip)
- ✅ Docker installed (optional, for full stack)
- ✅ 4GB+ RAM available
- ✅ 10GB+ disk space

## 5-Minute Setup (Local)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone <your-repo-url>
cd AI_Auditor

# Install dependencies with Poetry (recommended)
poetry install

# OR with pip
pip install -r requirements.txt
```

### Step 2: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env - Minimum required settings:
# API_KEY=your-secret-key-here
# API_KEY_ENABLED=true
```

### Step 3: Run

```bash
# Start the application
poetry run python -m app.main

# OR
python -m app.main
```

✅ **Server running at** `http://localhost:8000`

## First API Calls

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

### 2. Ingest a Document

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "X-API-Key: your-secret-key-here" \
  -F "file=@sample.pdf"
```

### 3. Query the System

```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: your-secret-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the revenue?"}'
```

## Docker Setup (Recommended for Production)

### Quick Start with Docker Compose

```bash
# Start all services (AI Auditor + Milvus + Prometheus + Grafana)
docker-compose up -d

# View logs
docker-compose logs -f ai-auditor

# Stop all services
docker-compose down
```

### Access Services:
- **AI Auditor API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Development Mode

### Running Tests

```bash
# Run all tests
make test

# Run specific test
pytest tests/test_security.py -v

# Run with coverage
make test
```

### Code Formatting

```bash
# Format code
make format

# Run linters
make lint

# Run all checks
make check
```

### Development Server with Auto-reload

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration Guide

### Essential Settings (.env)

```bash
# Application
APP_NAME=AI Auditor
ENVIRONMENT=development  # or production
PORT=8000

# Security (REQUIRED)
API_KEY_ENABLED=true
API_KEY=generate-a-strong-key-here
ALLOWED_ORIGINS=http://localhost:3000

# Vector Store
USE_MILVUS=false  # true for production
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Optional: LLM Integration
USE_LLM=false
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
```

### Generate API Key

```python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Testing the System

### 1. Create a Test PDF

Save this as `test_document.txt` (or use any PDF):
```
Financial Report Q1 2024

Revenue: $10 million
Expenses: $7 million
Net Income: $3 million
```

### 2. Ingest the Document

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "X-API-Key: your-api-key" \
  -F "file=@test_document.pdf"
```

### 3. Query It

```bash
curl -X POST "http://localhost:8000/query" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the revenue in Q1 2024?"}'
```

## Common Issues & Solutions

### Issue: Import errors when running

**Solution**: Install dependencies
```bash
poetry install
# or
pip install -r requirements.txt
```

### Issue: Port 8000 already in use

**Solution**: Change port in .env
```bash
PORT=8001
```

### Issue: API key authentication failing

**Solution**: Disable for testing
```bash
API_KEY_ENABLED=false
```

### Issue: Out of memory errors

**Solution**: Enable UMAP dimensionality reduction
```bash
DRIFT_USE_UMAP=true
DRIFT_UMAP_COMPONENTS=32
```

## Next Steps

### 1. Enable LLM (Optional)

```bash
# Add to .env
USE_LLM=true
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### 2. Enable Milvus (For Scale)

```bash
# Start with docker-compose (includes Milvus)
docker-compose up -d

# Update .env
USE_MILVUS=true
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. Enable Monitoring

```bash
# Already included in docker-compose
# Access Grafana at http://localhost:3000
```

### 4. Deploy to Production

See deployment guides:
- [Docker Deployment](README.md#docker)
- [Kubernetes Deployment](README.md#kubernetes)

## Useful Commands

```bash
# Development
make install      # Install dependencies
make run         # Run application
make test        # Run tests
make format      # Format code

# Docker
make docker-build # Build image
make docker-run  # Run with compose

# Monitoring
curl http://localhost:8000/metrics  # Prometheus metrics
curl http://localhost:8000/health/detailed  # Health check
```

## Getting Help

- 📖 Read the [full documentation](README.md)
- 🐛 [Report issues](https://github.com/your-repo/issues)
- 💬 [Ask questions](https://github.com/your-repo/discussions)
- 📧 Email: support@example.com

## What's Next?

1. ✅ System is running
2. ✅ You've made your first API calls
3. 📚 Read the [complete README](README.md)
4. 🔒 Review [security best practices](README.md#security-best-practices)
5. 🚀 [Deploy to production](README.md#deployment)

---

**Congratulations!** 🎉 Your AI Auditor system is up and running!
