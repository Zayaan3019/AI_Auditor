# AI Auditor

Production-grade multimodal RAG engine for financial documents with drift detection.

## Features

- **🔒 Security First**: API key authentication, rate limiting, input validation, CORS protection
- **📊 Comprehensive Monitoring**: Prometheus metrics, detailed health checks, Sentry integration
- **⚡ High Performance**: Async operations, connection pooling, caching support
- **🎯 Drift Detection**: IsolationForest-based drift detection with optional UMAP dimensionality reduction
- **🔄 Flexible Vector Store**: FAISS (local) or Milvus (distributed) support
- **🤖 LLM Integration**: Support for OpenAI, Anthropic, and Azure OpenAI
- **📦 Production Ready**: Docker, Kubernetes, CI/CD pipelines included
- **✅ Well Tested**: Comprehensive unit and integration tests

## Quick Start

### Prerequisites

- Python 3.10 or 3.11
- Poetry (recommended) or pip
- Docker (optional)

### Installation

1. Clone and install:
```bash
git clone <repo-url>
cd AI_Auditor
poetry install
```

2. Configure:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Run:
```bash
python -m app.main
```

API available at `http://localhost:8000`

## API Endpoints

### Ingest Document
```bash
curl -X POST "http://localhost:8000/ingest" \\
  -H "X-API-Key: your-api-key" \\
  -F "file=@document.pdf"
```

### Query Documents
```bash
curl -X POST "http://localhost:8000/query" \\
  -H "X-API-Key: your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "What is the revenue for Q1?"}'
```

### Health Check
- `GET /health` - Basic health
- `GET /health/detailed` - Detailed component status
- `GET /metrics` - Prometheus metrics

## Configuration

See `.env.example` for all options. Key settings:

- `API_KEY_ENABLED` - Enable authentication
- `USE_LLM` - Enable LLM generation
- `USE_MILVUS` - Use Milvus vector store
- `SENTRY_DSN` - Error tracking

## Deployment

### Docker
```bash
docker-compose up -d
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
```

## Development

```bash
# Tests
pytest --cov=app

# Format
black app/ tests/
isort app/ tests/

# Lint
flake8 app/ tests/
mypy app/
```

## Security Best Practices

1. Enable API keys: `API_KEY_ENABLED=true`
2. Restrict CORS: `ALLOWED_ORIGINS=https://yourdomain.com`
3. Enable rate limiting: `RATE_LIMIT_ENABLED=true`
4. Use HTTPS in production
5. Enable monitoring: `SENTRY_DSN=<your-dsn>`

## License

MIT License
