from __future__ import annotations

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch

from app.services.vector_store import VectorStoreManager, VectorStoreError


@pytest.mark.asyncio
async def test_vector_store_singleton():
    """Test that VectorStoreManager is a singleton."""
    vs1 = VectorStoreManager.get_instance(embedding_model="test-model")
    vs2 = VectorStoreManager.get_instance(embedding_model="another-model")
    assert vs1 is vs2


@pytest.mark.asyncio
async def test_add_documents():
    """Test adding documents to vector store."""
    vs = VectorStoreManager(embedding_model="all-MiniLM-L6-v2", use_milvus=False)

    chunks = [
        {"text": "Test document 1", "metadata": {"source": "test.pdf"}},
        {"text": "Test document 2", "metadata": {"source": "test.pdf"}},
    ]

    # Mock the embedding client
    mock_embeddings = Mock()
    mock_embeddings.embed_documents = Mock(
        return_value=[[0.1] * 384, [0.2] * 384]
    )
    vs._embeddings_client = mock_embeddings

    ids = await vs.add_documents(chunks)

    assert len(ids) == 2
    assert len(vs._embeddings) == 2
    assert len(vs._texts) == 2


@pytest.mark.asyncio
async def test_similarity_search_without_vectorstore():
    """Test similarity search using cached embeddings."""
    vs = VectorStoreManager(embedding_model="all-MiniLM-L6-v2", use_milvus=False)

    # Add some embeddings manually
    vs._embeddings = [np.ones(384, dtype=np.float32), np.ones(384, dtype=np.float32) * 0.5]
    vs._texts = ["Document 1", "Document 2"]
    vs._metadatas = [{"source": "test1.pdf"}, {"source": "test2.pdf"}]

    # Mock embedding client
    mock_embeddings = Mock()
    mock_embeddings.embed_query = Mock(return_value=[0.9] * 384)
    vs._embeddings_client = mock_embeddings

    results = await vs.similarity_search("test query", k=2)

    assert len(results) <= 2
    assert all(isinstance(r, dict) for r in results)
    assert all("text" in r and "score" in r and "metadata" in r for r in results)


@pytest.mark.asyncio
async def test_get_all_embeddings():
    """Test retrieving all embeddings."""
    vs = VectorStoreManager(embedding_model="all-MiniLM-L6-v2", use_milvus=False)

    vs._embeddings = [np.ones(384, dtype=np.float32) * i for i in range(3)]

    embeddings = await vs.get_all_embeddings()

    assert embeddings.shape == (3, 384)
    assert np.allclose(embeddings[0], np.ones(384))
