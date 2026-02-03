from __future__ import annotations

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.api.routes import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_api_key():
    """Mock API key validation for tests."""
    with patch("app.core.security.api_key_validator.validate", return_value=True):
        yield


@pytest.fixture
def mock_rate_limit():
    """Mock rate limiting for tests."""
    with patch("app.core.security.rate_limiter.is_allowed", return_value=True):
        yield


def test_health_endpoint(client):
    """Test basic health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_detailed_health_endpoint(client):
    """Test detailed health endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime_seconds" in data
    assert "checks" in data
    assert "timestamp" in data


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "ai_auditor" in response.text


def test_query_missing_api_key(client):
    """Test query endpoint without API key."""
    with patch("app.core.config.settings.api_key_enabled", True):
        response = client.post("/query", json={"query": "test"})
        assert response.status_code == 401


def test_query_with_api_key(client, mock_api_key, mock_rate_limit):
    """Test query endpoint with valid API key."""
    with patch("app.api.routes.rag_engine.answer") as mock_answer:
        mock_answer.return_value = {
            "answer": "Test answer",
            "drift_score": 0.5,
            "is_outlier": False,
            "sources": [],
        }

        response = client.post(
            "/query",
            json={"query": "test query"},
            headers={"X-API-Key": "test-key"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "drift_score" in data
        assert "is_outlier" in data
        assert "sources" in data


def test_query_empty_string(client, mock_api_key, mock_rate_limit):
    """Test query endpoint with empty query."""
    response = client.post(
        "/query", json={"query": ""}, headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 422  # Validation error


def test_ingest_invalid_file_type(client, mock_api_key, mock_rate_limit):
    """Test ingest endpoint with non-PDF file."""
    response = client.post(
        "/ingest",
        files={"file": ("test.txt", b"test content", "text/plain")},
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 400


def test_rate_limiting(client, mock_api_key):
    """Test rate limiting functionality."""
    with patch("app.core.security.rate_limiter.is_allowed", return_value=False):
        response = client.post(
            "/query",
            json={"query": "test"},
            headers={"X-API-Key": "test-key"},
        )
        assert response.status_code == 429
