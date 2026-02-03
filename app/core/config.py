from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from loguru import logger


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Uses Pydantic `BaseSettings` to allow `.env` files or environment
    variables to override defaults.
    """

    # Application
    app_name: str = "AI Auditor"
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Security
    api_key_enabled: bool = True
    api_key: Optional[str] = None
    allowed_origins: str = "*"
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    max_file_size_mb: int = 50

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_cache_size: int = 1000

    # Vector store
    use_milvus: bool = False
    milvus_host: Optional[str] = None
    milvus_port: Optional[int] = None
    milvus_collection: str = "ai_auditor"
    vector_store_cache_ttl: int = 3600

    # Drift detector
    drift_use_umap: bool = False
    drift_umap_components: int = 64
    drift_contamination: float = 0.01
    drift_retrain_threshold: int = 100

    # RAG Engine
    rag_top_k: int = 5
    rag_chunk_size: int = 1000
    rag_chunk_overlap: int = 200
    rag_use_reranking: bool = False

    # Storage
    storage_dir: Optional[Path] = None
    backup_enabled: bool = True
    backup_interval_hours: int = 24

    # Monitoring
    prometheus_enabled: bool = True
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "production"
    health_check_interval: int = 30

    # Performance
    max_workers: int = 4
    request_timeout: int = 30
    pool_size: int = 10
    cache_enabled: bool = True
    cache_type: str = "memory"

    # LLM Integration (Optional)
    use_llm: bool = False
    llm_provider: str = Field(default="openai", pattern="^(openai|anthropic|azure)$")
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    anthropic_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_key: Optional[str] = None
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1000, ge=1, le=4096)

    @validator("storage_dir", pre=True, always=True)
    def set_storage_dir(cls, v):
        if v is None:
            v = Path("./data")
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @validator("api_key")
    def validate_api_key_in_production(cls, v, values):
        if values.get("environment") == "production" and values.get("api_key_enabled") and not v:
            logger.warning("API key should be set in production environment")
        return v

    @validator("allowed_origins")
    def validate_origins_in_production(cls, v, values):
        if values.get("environment") == "production" and v == "*":
            logger.warning("CORS should be restricted in production environment")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


settings = Settings()
