from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Vector DB settings
    chroma_persist_directory: str = "./chroma_db"
    collection_name: str = "gcp_documents"

    # PDF settings
    pdf_path: str = "./Google Cloud Platform (GCP).pdf"
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # App settings
    app_title: str = "GCP Knowledge Assistant"
    max_context_chunks: int = 5

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
