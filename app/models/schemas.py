from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Response returned after successful ingestion."""

    status: str
    chunks_added: int
    ids: List[str]


class QueryRequest(BaseModel):
    """Incoming query payload."""

    query: str = Field(..., min_length=1)


class SourceItem(BaseModel):
    text: str
    score: float
    metadata: Dict[str, Any]


class QueryResponse(BaseModel):
    """Response returned for query endpoint."""

    answer: str
    drift_score: float
    is_outlier: bool
    sources: List[SourceItem]


class HealthResponse(BaseModel):
    status: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response with component statuses."""

    status: str
    uptime_seconds: float
    checks: Dict[str, bool]
    timestamp: float
