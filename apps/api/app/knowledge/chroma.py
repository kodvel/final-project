"""ChromaDB collection setup and persistence helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

COMPANY_KNOWLEDGE_COLLECTION = "company_knowledge"

_chroma_client = None


def get_chroma_client():
    """Return a singleton PersistentClient using Settings.chroma_persist_directory.

    Returns None if chromadb is not importable (test/dev environments).
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    try:
        import chromadb
    except ImportError:
        logger.warning("chromadb not installed; vector indexing disabled")
        return None

    from app.core.config import get_settings

    settings = get_settings()
    _chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    return _chroma_client


def get_company_knowledge_collection():
    """Return the ``company_knowledge`` collection (created if absent).

    Returns None when chromadb is unavailable.
    """
    client = get_chroma_client()
    if client is None:
        return None
    return client.get_or_create_collection(
        name=COMPANY_KNOWLEDGE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def reset_chroma_client() -> None:
    """Reset the singleton client (useful for tests)."""
    global _chroma_client
    _chroma_client = None
