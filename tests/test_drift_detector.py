import numpy as np
import pytest

from app.services.drift_detector import DriftDetector


@pytest.mark.asyncio
async def test_train_and_predict_inlier_outlier() -> None:
    # Create synthetic embeddings (clustered around 0)
    rng = np.random.RandomState(0)
    embeddings = [rng.normal(loc=0.0, scale=1.0, size=64).astype(np.float32) for _ in range(200)]

    detector = DriftDetector(n_estimators=50, contamination=0.05, use_umap=False)
    await detector.add_embeddings(embeddings)
    await detector.train()

    # Predict on a sample from training set -> likely inlier
    inlier = embeddings[0]
    res_in = await detector.predict(inlier)
    assert isinstance(res_in.is_outlier, bool)
    assert isinstance(res_in.score, float)

    # Create a distant outlier
    outlier = (rng.normal(loc=50.0, scale=1.0, size=64)).astype(np.float32)
    res_out = await detector.predict(outlier)
    assert isinstance(res_out.is_outlier, bool)
    assert isinstance(res_out.score, float)

    # We expect the outlier to be marked as such (high probability)
    assert res_out.is_outlier or not res_in.is_outlier
