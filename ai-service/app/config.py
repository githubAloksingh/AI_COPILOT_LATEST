import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.7-flash"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_candidate_models: List[str] = [
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    gemini_embedding_candidate_models: List[str] = [
        "text-embedding-004",
        "gemini-embedding-001",
        "gemini-embedding-2"
    ]

    # Chroma
    chroma_url: str = "http://localhost:8001"
    chroma_collection: str = "ai_work_copilot"
    chroma_persist_directory: str = "./chroma_data"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 5

    # App
    host: str = "0.0.0.0"
    port: int = 8000


settings = Settings()
