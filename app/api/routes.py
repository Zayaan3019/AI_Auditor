from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, FastAPI, File, UploadFile, Depends
from fastapi.responses import Response
from loguru import logger

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.exceptions import bad_request, internal_error
from app.core.security import verify_api_key, check_rate_limit, validate_file_upload, SecurityError
from app.core.middleware import (
    setup_cors,
    RequestLoggingMiddleware,
    RequestIDMiddleware,
    ErrorHandlingMiddleware,
)
from app.core.monitoring import health_checker, collect_metrics_background
from app.models.schemas import (
    IngestResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    SourceItem,
    DetailedHealthResponse,
)
from app.ingestion.loader import extract_text_from_pdf_bytes
from app.ingestion.chunker import chunk_text
from app.services.vector_store import VectorStoreManager
from app.services.drift_detector import DriftDetector
from app.services.rag_engine import RAGEngine


router = APIRouter()

# Initialize singleton components
vector_store = VectorStoreManager.get_instance(
    embedding_model=settings.embedding_model, use_milvus=settings.use_milvus, milvus_config={
        "host": settings.milvus_host,
        "port": settings.milvus_port,
        "collection_name": settings.milvus_collection,
    },
)

drift_detector = DriftDetector(
    n_estimators=100,
    contamination=settings.drift_contamination,
    use_umap=settings.drift_use_umap,
    umap_n_components=settings.drift_umap_components,
)

rag_engine = RAGEngine(vector_store=vector_store, drift_detector=drift_detector)

# Retrain queue and worker
_retrain_queue: "asyncio.Queue[str]" = asyncio.Queue()

# Metrics
INGEST_COUNTER = Counter("ai_auditor_ingest_total", "Total number of ingests")
QUERY_COUNTER = Counter("ai_auditor_query_total", "Total number of queries")
DRIFT_COUNTER = Counter("ai_auditor_drift_total", "Total number of drift detections")
QUERY_LATENCY = Histogram("ai_auditor_query_seconds", "Query latency seconds")


async def _retrain_drift_detector() -> None:
    """Fetch embeddings and retrain the drift detector."""
    X = await vector_store.get_all_embeddings()
    if X.size == 0:
        return
    await drift_detector.reset()
    await drift_detector.add_embeddings([x for x in list(X)])
    await drift_detector.train()


async def _retrain_worker() -> None:
    """Background worker that coalesces retrain requests and retrains once.

    This worker runs for the lifetime of the app; on each item it drains
    the queue to avoid repeated retrains when many ingests happen.
    """
    while True:
        try:
            item = await _retrain_queue.get()
            # Drain remaining items to coalesce
            while not _retrain_queue.empty():
                try:
                    _retrain_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            try:
                await _retrain_drift_detector()
            except Exception:
                # Log and continue; do not crash the worker
                pass
        except asyncio.CancelledError:
            break


@router.post("/ingest", response_model=IngestResponse, dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """Ingest a PDF file, chunk it, add to vector DB, and enqueue drift retrain."""
    # Validate file
    try:
        file_content = await file.read()
        file_size = len(file_content)
        validate_file_upload(file.filename, file_size)
    except SecurityError as e:
        raise bad_request(str(e))

    try:
        text = await extract_text_from_pdf_bytes(file_content)
    except Exception as exc:
        logger.exception(f"Failed to extract text from PDF: {exc}")
        raise internal_error(f"Failed to process PDF file: {exc}")

    chunks = chunk_text(text, chunk_size=settings.rag_chunk_size, overlap=settings.rag_chunk_overlap)
    
    if not chunks:
        raise bad_request("No text could be extracted from the PDF file")

    doc_chunks = [{"text": c, "metadata": {"source": file.filename}} for c in chunks]

    try:
        ids = await vector_store.add_documents(doc_chunks)
    except Exception as exc:
        logger.exception(f"Failed to add documents to vector store: {exc}")
        raise internal_error(f"Failed to add documents to vector store: {exc}")

    # enqueue retrain (debounced by worker)
    try:
        _retrain_queue.put_nowait(file.filename)
    except asyncio.QueueFull:
        # Best-effort: if the queue is full, drop the event
        logger.warning("Retrain queue full, skipping retrain request")

    INGEST_COUNTER.inc()

    logger.info(f"Successfully ingested {len(chunks)} chunks from {file.filename}")

    return IngestResponse(status="ok", chunks_added=len(chunks), ids=ids)


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def query(payload: QueryRequest) -> QueryResponse:
    """Run the RAG pipeline for a user query."""
    QUERY_COUNTER.inc()
    with QUERY_LATENCY.time():
        try:
            result = await rag_engine.answer(payload.query)
        except Exception as exc:
            logger.exception(f"Failed to run RAG pipeline: {exc}")
            raise internal_error(f"Failed to run RAG pipeline: {exc}")

    if result.get("is_outlier"):
        DRIFT_COUNTER.inc()
        logger.warning(f"Drift detected for query: {payload.query[:100]}...")

    sources = [SourceItem(text=s.get("text", ""), score=s.get("score", 0.0), metadata=s.get("metadata", {})) for s in result.get("sources", [])]

    return QueryResponse(answer=result["answer"], drift_score=result["drift_score"], is_outlier=result["is_outlier"], sources=sources)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(status="ok")


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health() -> DetailedHealthResponse:
    """Detailed health check with component status."""
    health_status = await health_checker.check_all()
    return DetailedHealthResponse(**health_status)


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Production-grade multimodal RAG engine for financial documents with drift detection",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # Setup CORS
    setup_cors(app)
    
    # Add middlewares (order matters!)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
    
    app.include_router(router)

    @app.on_event("startup")
    async def startup_tasks() -> None:
        logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
        
        # Start retrain worker
        worker = asyncio.create_task(_retrain_worker())
        app.state._retrain_worker = worker
        
        # Start metrics collection if enabled
        if settings.prometheus_enabled:
            metrics_task = asyncio.create_task(collect_metrics_background(interval=settings.health_check_interval))
            app.state._metrics_task = metrics_task
            logger.info("Metrics collection started")
        
        # Initialize Sentry if configured
        if settings.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.init(
                    dsn=settings.sentry_dsn,
                    environment=settings.sentry_environment,
                    traces_sample_rate=0.1,
                )
                logger.info("Sentry monitoring initialized")
            except ImportError:
                logger.warning("Sentry DSN configured but sentry-sdk not installed")
        
        logger.info("Application startup complete")

    @app.on_event("shutdown")
    async def shutdown_tasks() -> None:
        logger.info("Shutting down application")
        
        # Cancel retrain worker
        worker = getattr(app.state, "_retrain_worker", None)
        if worker is not None:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass
        
        # Cancel metrics task
        metrics_task = getattr(app.state, "_metrics_task", None)
        if metrics_task is not None:
            metrics_task.cancel()
            try:
                await metrics_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Application shutdown complete")

    return app


app = create_app()
