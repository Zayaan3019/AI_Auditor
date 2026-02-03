from __future__ import annotations

import asyncio
from typing import List, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest
try:  # umap is optional at runtime; only needed when `use_umap=True`
    import umap
except Exception:  # pragma: no cover - optional dependency
    umap = None  # type: ignore


class DriftResult(BaseModel):
    """Result for a drift prediction.

    Attributes:
        is_outlier: Whether the sample is considered an outlier by the detector.
        score: The decision function score; lower means more anomalous.
    """

    is_outlier: bool
    score: float


class DriftDetector:
    """IsolationForest-based drift detector trained on knowledge-base embeddings.

    This class keeps an internal buffer of embeddings representing the knowledge
    base and exposes async methods to (re)train and predict whether a query
    embedding is out-of-distribution relative to the KB.

    All public methods are async-friendly and offload CPU-bound work to a
    background thread.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.01,
        random_state: int = 42,
        use_umap: bool = False,
        umap_n_components: int = 64,
    ) -> None:
        """Initialize the detector.

        Args:
            n_estimators: Number of trees for IsolationForest.
            contamination: Expected proportion of outliers in data.
            random_state: RNG seed.
            use_umap: If True, reduce dimensionality with UMAP before training.
            umap_n_components: Target UMAP dimensions.
        """
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.use_umap = use_umap
        self.umap_n_components = umap_n_components

        self._embeddings: List[np.ndarray] = []
        self._model: Optional[IsolationForest] = None
        self._umap_mapper: Optional[umap.UMAP] = None
        self._lock: asyncio.Lock = asyncio.Lock()

    async def add_embeddings(self, embeddings: List[np.ndarray]) -> None:
        """Add embeddings to the internal KB buffer.

        Args:
            embeddings: List of 1-D numpy arrays.
        """
        async with self._lock:
            for e in embeddings:
                if not isinstance(e, np.ndarray):
                    raise TypeError("embeddings must be numpy arrays")
                self._embeddings.append(e.astype(np.float32))

    async def get_all_embeddings(self) -> np.ndarray:
        """Return all stored embeddings as a 2D numpy array.

        Returns:
            np.ndarray: shape (n_samples, dim)
        """
        async with self._lock:
            if not self._embeddings:
                return np.zeros((0, 0), dtype=np.float32)
            return np.stack(self._embeddings, axis=0)

    async def train(self) -> None:
        """Train the IsolationForest on current KB embeddings.

        This method will run training in a thread pool to avoid blocking the
        event loop.
        """
        async with self._lock:
            X = await self.get_all_embeddings()
        if X.size == 0:
            logger.warning("No embeddings available for training DriftDetector")
            return

        if self.use_umap and X.shape[1] > self.umap_n_components:
            # Perform UMAP reduction in threadpool
            if umap is None:
                raise RuntimeError("umap-learn is required when use_umap=True")
            def fit_umap(data: np.ndarray) -> umap.UMAP:
                mapper = umap.UMAP(n_components=self.umap_n_components, random_state=self.random_state)
                mapper.fit(data)
                return mapper

            mapper = await asyncio.to_thread(fit_umap, X)
            # assign under lock
            self._umap_mapper = mapper
            X_reduced = self._umap_mapper.transform(X)
        else:
            X_reduced = X

        def fit_iforest(data: np.ndarray) -> IsolationForest:
            model = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=self.contamination,
                random_state=self.random_state,
            )
            model.fit(data)
            return model

        model = await asyncio.to_thread(fit_iforest, X_reduced)
        async with self._lock:
            self._model = model
        logger.info("DriftDetector trained on %d samples", X_reduced.shape[0])

    async def predict(self, embedding: np.ndarray) -> DriftResult:
        """Predict whether a single embedding is an outlier.

        Args:
            embedding: 1-D numpy array for the query embedding.

        Returns:
            DriftResult: contains `is_outlier` and `score` (decision function).
        """
        async with self._lock:
            if self._model is None:
                raise RuntimeError("DriftDetector model is not trained")

            model = self._model
            mapper = self._umap_mapper

        if not isinstance(embedding, np.ndarray):
            raise TypeError("embedding must be a numpy array")

        x = embedding.astype(np.float32).reshape(1, -1)
        if mapper is not None:
            x = mapper.transform(x)

        def run_predict(m: IsolationForest, data: np.ndarray):
            score = m.decision_function(data)[0]
            pred = m.predict(data)[0]
            return float(score), int(pred)

        score, pred = await asyncio.to_thread(run_predict, model, x)

        # IsolationForest.predict returns 1 for inliers, -1 for outliers
        is_outlier = pred == -1

        return DriftResult(is_outlier=is_outlier, score=score)

    async def reset(self) -> None:
        """Clear buffer and model state."""
        self._embeddings = []
        self._model = None
        self._umap_mapper = None
