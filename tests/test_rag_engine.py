import numpy as np
import pytest

from app.services.rag_engine import RAGEngine
from app.services.drift_detector import DriftDetector


class FakeVectorStore:
    def __init__(self) -> None:
        self._texts = ["Revenue report Q1", "Balance sheet summary"]
        self._embeddings = [np.ones(32, dtype=np.float32), np.ones(32, dtype=np.float32) * 0.9]
        # fake embeddings client used by RAGEngine._embed_query
        class E:
            @staticmethod
            def embed_query(q: str):
                return np.ones(32).tolist()

        self._embeddings_client = E()

    async def similarity_search(self, query: str, k: int = 5):
        return [{"text": self._texts[0], "score": 0.95, "metadata": {}}]

    async def get_all_embeddings(self):
        return np.stack(self._embeddings)


@pytest.mark.asyncio
async def test_rag_engine_pipeline_returns_expected_structure() -> None:
    vs = FakeVectorStore()

    detector = DriftDetector(n_estimators=20, contamination=0.01, use_umap=False)
    # train detector on fake VS embeddings
    await detector.add_embeddings([e for e in vs._embeddings])
    await detector.train()

    engine = RAGEngine(vector_store=vs, drift_detector=detector)
    result = await engine.answer("What is the revenue for Q1?")

    assert "answer" in result
    assert "drift_score" in result
    assert "is_outlier" in result
    assert isinstance(result["sources"], list)
