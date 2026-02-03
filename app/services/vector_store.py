from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

try:
    from langchain.embeddings import HuggingFaceEmbeddings
    from langchain.vectorstores import FAISS
except Exception:  # pragma: no cover - handled at runtime
    HuggingFaceEmbeddings = None  # type: ignore
    FAISS = None  # type: ignore

try:
    # langchain_community provides Milvus wrapper
    from langchain_community.vectorstores import Milvus
except Exception:  # pragma: no cover - handled at runtime
    Milvus = None  # type: ignore


class VectorStoreError(Exception):
    """Custom error for vector store operations."""


class VectorStoreManager:
    """Singleton manager for vector DB (FAISS local or Milvus remote).

    This class centralizes embedding creation, persistence, and similarity
    search. It keeps a local cache of embeddings to support training the
    drift detector.
    """

    _instance: Optional["VectorStoreManager"] = None

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        use_milvus: bool = False,
        milvus_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the manager.

        Args:
            embedding_model: HuggingFace sentence-transformers model name.
            use_milvus: Whether to use Milvus backend.
            milvus_config: Milvus connection configuration.
        """
        self.embedding_model = embedding_model
        self.use_milvus = use_milvus
        self.milvus_config = milvus_config or {}

        self._embeddings: List[np.ndarray] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._texts: List[str] = []

        self._vectorstore = None
        self._embeddings_client = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._client_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def get_instance(cls, **kwargs: Any) -> "VectorStoreManager":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    async def _ensure_embedding_client(self) -> None:
        """Lazily initialize the embedding client."""
        async with self._client_lock:
            if self._embeddings_client is not None:
                return

            if HuggingFaceEmbeddings is None:
                raise VectorStoreError("HuggingFaceEmbeddings is not available")

            def init_client():
                return HuggingFaceEmbeddings(model_name=self.embedding_model)

            self._embeddings_client = await asyncio.to_thread(init_client)
            logger.info("Embedding client initialized using %s", self.embedding_model)

    async def add_documents(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Add document chunks to the vector store.

        Each chunk should be a dict with keys: `text` (str) and optional
        `metadata` (dict). This method computes embeddings, stores them in
        the backend, and caches them locally for drift training.

        Args:
            chunks: List of chunk dictionaries.

        Returns:
            List of ids (if available) or generated ids.
        """
        await self._ensure_embedding_client()

        texts: List[str] = [c["text"] for c in chunks]
        metadatas: List[Dict[str, Any]] = [c.get("metadata", {}) for c in chunks]

        def embed_texts(texts_batch: List[str]):
            return self._embeddings_client.embed_documents(texts_batch)  # type: ignore

        embeddings = await asyncio.to_thread(embed_texts, texts)

        # convert to numpy arrays and cache
        ids: List[str] = []
        async with self._lock:
            for i, emb in enumerate(embeddings):
                arr = np.array(emb, dtype=np.float32)
                self._embeddings.append(arr)
                self._metadatas.append(metadatas[i])
                self._texts.append(texts[i])
                ids.append(str(len(self._texts) - 1))

        # Persist to vectorstore backend
        if self.use_milvus and Milvus is not None:
            if self._vectorstore is None:
                # create milvus collection and vectorstore
                def init_milvus():
                    return Milvus(
                        embedding_function=self._embeddings_client,
                        collection_name=self.milvus_config.get("collection_name", "ai_auditor"),
                        **self.milvus_config,
                    )

                self._vectorstore = await asyncio.to_thread(init_milvus)

            def add_to_milvus(vs, texts_batch, mets):
                return vs.add_texts(texts_batch, metadatas=mets)

            await asyncio.to_thread(add_to_milvus, self._vectorstore, texts, metadatas)
        else:
            # Use FAISS in-memory index
            if FAISS is None:
                raise VectorStoreError("FAISS vectorstore is not available")

            def init_or_add_faiss():
                if self._vectorstore is None:
                    self._vectorstore = FAISS.from_texts(
                        texts, self._embeddings_client, metadatas=metadatas
                    )
                else:
                    self._vectorstore.add_texts(texts, metadatas=metadatas)

            await asyncio.to_thread(init_or_add_faiss)

        return ids

    async def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform a similarity search for `query` and return top-k hits.

        Returns a list of dicts with `text`, `score`, and `metadata`.
        """
        await self._ensure_embedding_client()

        def embed_query(q: str):
            return self._embeddings_client.embed_query(q)  # type: ignore

        q_emb = await asyncio.to_thread(embed_query, query)

        if self._vectorstore is None:
            # Fall back to simple cosine against cached embeddings
            async with self._lock:
                if not self._embeddings:
                    return []
                qv = np.array(q_emb, dtype=np.float32)
                sims: List[Tuple[int, float]] = []
                for idx, emb in enumerate(self._embeddings):
                    score = float(np.dot(qv, emb) / (np.linalg.norm(qv) * np.linalg.norm(emb) + 1e-12))
                    sims.append((idx, score))
                sims.sort(key=lambda x: x[1], reverse=True)
                results = []
                for idx, score in sims[:k]:
                    results.append({"text": self._texts[idx], "score": score, "metadata": self._metadatas[idx]})
                return results

        # Use vectorstore's similarity search
        def vs_search(vs, q, topk):
            return vs.similarity_search_with_score(q, k=topk)

        hits = await asyncio.to_thread(vs_search, self._vectorstore, query, k)

        # hits are tuples (Document, score) depending on backend
        results: List[Dict[str, Any]] = []
        for doc, score in hits:
            md = getattr(doc, "metadata", {}) or {}
            txt = getattr(doc, "page_content", str(doc))
            results.append({"text": txt, "score": float(score), "metadata": md})

        return results

    async def get_all_embeddings(self) -> np.ndarray:
        """Return cached embeddings as a 2D numpy array.

        Note: If using Milvus and the process restarted, cached embeddings
        may be empty. In a production deployment, consider reloading from
        the persistent store.
        """
        async with self._lock:
            if not self._embeddings:
                return np.zeros((0, 0), dtype=np.float32)
            return np.stack(self._embeddings, axis=0)
