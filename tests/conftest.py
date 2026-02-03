"""
Pytest configuration and shared fixtures.
"""
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    from app.services.vector_store import VectorStoreManager
    
    # Reset VectorStoreManager singleton
    VectorStoreManager._instance = None
    
    yield
    
    # Cleanup after test
    VectorStoreManager._instance = None


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    with patch("app.core.config.settings") as mock:
        mock.api_key_enabled = False
        mock.rate_limit_enabled = False
        mock.max_file_size_mb = 50
        mock.embedding_model = "all-MiniLM-L6-v2"
        mock.use_milvus = False
        mock.rag_top_k = 5
        mock.rag_chunk_size = 1000
        mock.rag_chunk_overlap = 200
        mock.use_llm = False
        yield mock


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return b"%PDF-1.4\nTest content"


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return "This is a test document with financial information. Revenue was $10M in Q1."
