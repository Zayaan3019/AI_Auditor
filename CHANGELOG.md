# AI Auditor - Change Log

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-02-02

### Added

#### Security
- API key authentication with secure hashing
- Rate limiting per IP address
- Input validation and sanitization
- File upload validation (size, type, path traversal)
- CORS configuration with origin restrictions
- Request ID tracking for all requests

#### Monitoring & Observability
- Comprehensive Prometheus metrics
  - HTTP request metrics (count, latency, errors)
  - System metrics (CPU, memory, disk)
  - Application metrics (vector store size, drift detector status)
- Detailed health check endpoint with component status
- Sentry integration for error tracking
- Structured logging with request context

#### LLM Integration
- Support for OpenAI GPT models
- Support for Anthropic Claude models
- Support for Azure OpenAI
- Configurable generation parameters
- Graceful fallback when LLM unavailable

#### Production Features
- Enhanced error handling middleware
- Request logging middleware
- Circuit breaker patterns
- Background metrics collection
- Graceful shutdown handling
- Docker Compose configuration with Milvus, Prometheus, Grafana
- Kubernetes deployment manifests
- Horizontal Pod Autoscaler configuration

#### Testing
- Comprehensive unit tests for all modules
- Integration tests for API endpoints
- Security tests for authentication and validation
- Test coverage reporting

#### Documentation
- Comprehensive README with examples
- API documentation improvements
- Configuration guide
- Deployment guides (Docker, Kubernetes)
- Security best practices
- Troubleshooting guide

#### CI/CD
- GitHub Actions workflow
- Automated testing (lint, test, security)
- Docker image building and publishing
- Code coverage reporting

### Changed
- Enhanced configuration system with validation
- Improved chunking with configurable parameters
- Better error messages and exception handling
- RAG engine supports optional reranking
- Drift detector with configurable retraining threshold

### Fixed
- Memory leaks in rate limiter (added cleanup)
- Thread safety in vector store operations
- Error handling in PDF extraction
- Proper async/await in all endpoints

## [0.1.0] - Initial Release

### Added
- Basic RAG engine with FAISS vector store
- PDF document ingestion
- Query endpoint with drift detection
- Simple health check
- Docker support
- Basic tests

---

## Upcoming Features (Roadmap)

### v0.3.0
- [ ] Query result caching
- [ ] Streaming responses for LLM
- [ ] Cross-encoder reranking
- [ ] Document versioning
- [ ] Backup and restore functionality

### v0.4.0
- [ ] Multi-modal support (images, tables)
- [ ] Multi-tenancy
- [ ] GraphQL API
- [ ] WebSocket support
- [ ] Advanced analytics dashboard
