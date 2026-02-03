from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from loguru import logger

from .vector_store import VectorStoreManager, VectorStoreError
from .drift_detector import DriftDetector, DriftResult
from app.core.config import settings


class RAGError(Exception):
    """Exception raised for RAG engine errors."""


class LLMGenerator:
    """Handles LLM-based answer generation with multiple provider support."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    async def _ensure_client(self) -> None:
        """Lazily initialize LLM client."""
        if self._client is not None:
            return

        if self.provider == "openai":
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            except ImportError:
                raise RAGError("openai package not installed. Run: pip install openai")
        elif self.provider == "anthropic":
            try:
                from anthropic import AsyncAnthropic

                self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            except ImportError:
                raise RAGError("anthropic package not installed. Run: pip install anthropic")
        elif self.provider == "azure":
            try:
                from openai import AsyncAzureOpenAI

                self._client = AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    api_version="2024-02-01",
                    azure_endpoint=settings.azure_openai_endpoint,
                )
            except ImportError:
                raise RAGError("openai package not installed. Run: pip install openai")
        else:
            raise RAGError(f"Unsupported LLM provider: {self.provider}")

    async def generate(self, query: str, context_docs: List[Dict[str, Any]]) -> str:
        """Generate answer using LLM.

        Args:
            query: User's question.
            context_docs: Retrieved documents with 'text' and 'metadata'.

        Returns:
            Generated answer string.
        """
        await self._ensure_client()

        # Prepare context from retrieved documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            source = metadata.get("source", "Unknown")
            context_parts.append(f"[{i}] Source: {source}\\n{text}")

        context = "\\n\\n".join(context_parts)

        # Build prompt
        system_prompt = (
            "You are an AI assistant specialized in analyzing financial documents. "
            "Use ONLY the provided context to answer questions accurately and concisely. "
            "If the context doesn't contain sufficient information, say so explicitly. "
            "Always cite the source number [N] when referencing information."
        )

        user_prompt = f"""Context from financial documents:
{context}

Question: {query}

Please provide a clear, accurate answer based solely on the context above."""

        try:
            if self.provider in ("openai", "azure"):
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content.strip()

            elif self.provider == "anthropic":
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text.strip()

        except Exception as exc:
            logger.exception(f"LLM generation failed: {exc}")
            raise RAGError(f"Failed to generate answer: {exc}")


class RAGEngine:
    """Retrieval-Augmented Generation engine with drift detection.

    Pipeline:
        Query -> Embedding -> Drift Check -> Retrieval -> [Reranking] -> Generation

    The engine is async and supports multiple LLM providers or falls back to
    a simple summarization when no LLM is configured.
    """

    def __init__(
        self,
        vector_store: VectorStoreManager,
        drift_detector: DriftDetector,
        generation_fn: Optional[Callable[[str, List[Dict[str, Any]]], Any]] = None,
        top_k: int = None,
        use_llm: bool = None,
    ) -> None:
        """Create a RAGEngine instance.

        Args:
            vector_store: Instance of `VectorStoreManager`.
            drift_detector: Instance of `DriftDetector`.
            generation_fn: Optional async callable to produce final answer.
            top_k: Number of retrieval results to use for generation.
            use_llm: Whether to use LLM for generation.
        """
        self.vector_store = vector_store
        self.drift_detector = drift_detector
        self.generation_fn = generation_fn
        self.top_k = top_k or 5
        self.use_llm = use_llm if use_llm is not None else False

        # Initialize LLM generator if enabled
        self.llm_generator = None
        if self.use_llm:
            from app.core.config import settings
            self.llm_generator = LLMGenerator(
                provider=settings.llm_provider,
                model=settings.openai_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

    async def _embed_query(self, query: str) -> np.ndarray:
        """Compute embedding for a query using the vector store's client.

        Returns:
            Numpy array embedding.
        """
        await self.vector_store._ensure_embedding_client()

        def embed(q: str):
            return self.vector_store._embeddings_client.embed_query(q)  # type: ignore

        emb = await asyncio.to_thread(embed, query)
        return np.array(emb, dtype=np.float32)

    async def _rerank_documents(
        self, query: str, docs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder (optional enhancement).

        Args:
            query: User query.
            docs: Retrieved documents.

        Returns:
            Reranked documents.
        """
        # Placeholder for reranking logic
        # In production, you could use sentence-transformers cross-encoder
        # or a dedicated reranking API
        from app.core.config import settings
        if not settings.rag_use_reranking:
            return docs

        # For now, just return as-is
        # TODO: Implement cross-encoder reranking
        logger.debug("Reranking not yet implemented, returning original order")
        return docs

    async def _fallback_generate(self, query: str, docs: List[Dict[str, Any]]) -> str:
        """Simple deterministic fallback generator combining retrieved texts.

        This ensures the API can always return a helpful answer even without
        an LLM backend configured.
        """
        if not docs:
            return "No relevant information found in the ingested documents."

        snippets = []
        for i, d in enumerate(docs[: self.top_k], 1):
            text = d.get("text", "")
            metadata = d.get("metadata", {})
            source = metadata.get("source", "Unknown")
            score = d.get("score", 0.0)
            snippets.append(f"[{i}] {source} (relevance: {score:.2f})\\n{text[:500]}...")

        joined = "\\n\\n".join(snippets)
        return f"""Based on the query: "{query}"

I found {len(snippets)} relevant excerpts from the financial documents:

{joined}

Note: This is a direct retrieval result. For more sophisticated analysis, consider enabling LLM integration."""

    async def answer(self, query: str) -> Dict[str, Any]:
        """Run the full RAG pipeline for `query`.

        Returns:
            Dict containing `answer`, `drift_score`, `is_outlier`, and `sources`.
        """
        if not query or not isinstance(query, str):
            raise RAGError("query must be a non-empty string")

        # Sanitize input
        from app.core.security import sanitize_input

        query = sanitize_input(query, max_length=2000)

        try:
            q_emb = await self._embed_query(query)
        except Exception as exc:
            logger.exception("Failed to embed query")
            raise RAGError("Embedding failure") from exc

        # Drift detection
        try:
            drift: DriftResult = await self.drift_detector.predict(q_emb)
        except RuntimeError:
            # Model not trained: treat as not outlier but log
            logger.warning("DriftDetector not trained; treating query as in-distribution")
            drift = DriftResult(is_outlier=False, score=0.0)
        except Exception as exc:
            logger.exception("Drift detection failed")
            raise RAGError("Drift detection failure") from exc

        # Retrieval
        try:
            hits = await self.vector_store.similarity_search(query, k=self.top_k * 2)
        except VectorStoreError:
            logger.exception("VectorStore similarity search failed")
            hits = []
        except Exception:
            logger.exception("Unexpected error during similarity search")
            hits = []

        # Reranking (optional)
        if hits:
            hits = await self._rerank_documents(query, hits)
            hits = hits[: self.top_k]

        # Generation
        try:
            if self.generation_fn is not None:
                # Custom generation function
                result = self.generation_fn(query, hits)
                if asyncio.iscoroutine(result):
                    answer = await result  # type: ignore
                else:
                    answer = result  # type: ignore
            elif self.use_llm and self.llm_generator:
                # Use LLM generator
                answer = await self.llm_generator.generate(query, hits)
            else:
                # Fallback generator
                answer = await self._fallback_generate(query, hits)
        except Exception:
            logger.exception("Generation failed; returning fallback summary")
            answer = await self._fallback_generate(query, hits)

        # If drift detected, prepend a warning
        if drift.is_outlier:
            warning = (
                "⚠️ WARNING: This query appears to be outside the scope of the ingested "
                "financial documents (drift detected). The answer below may be speculative "
                "or less reliable.\\n\\n"
            )
            answer = f"{warning}{answer}"

        return {
            "answer": answer,
            "drift_score": float(drift.score),
            "is_outlier": bool(drift.is_outlier),
            "sources": hits,
        }
