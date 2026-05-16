"""ChromaDB collection setup and persistence helpers.

The collection uses an OpenAI-compatible embedding function configured from
project settings so that ``upsert(documents=...)`` and ``query(query_texts=...)``
auto-embed without the caller managing vectors.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

COMPANY_KNOWLEDGE_COLLECTION = "company_knowledge"

_chroma_client = None


class _OpenAIEmbeddingFunction:
    """ChromaDB-compatible embedding function backed by any OpenAI-compatible /embeddings endpoint.

    Works with OpenAI, Mistral (``https://api.mistral.ai/v1``), and other providers
    that expose the same request/response shape.
    """

    def __init__(self, api_base_url: str, api_key: str, model: str) -> None:
        self._api_base_url = api_base_url
        self._api_key = api_key
        self._model = model

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 — Chroma protocol
        if not input:
            return []

        from app.core.openai_client import create_openai_client

        client = create_openai_client(base_url=self._api_base_url, api_key=self._api_key)
        response = client.embeddings.create(model=self._model, input=input)

        sorted_data = sorted(response.data, key=lambda d: d.index)
        return [item.embedding for item in sorted_data]

    def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002 — Chroma protocol
        return self.__call__(input)

    @staticmethod
    def name() -> str:
        return "openai_compatible"

    def default_space(self) -> str:
        return "cosine"

    def supported_spaces(self) -> list[str]:
        return ["cosine", "l2", "ip"]

    def get_config(self) -> dict:
        return {
            "api_base_url": self._api_base_url,
            "model": self._model,
        }

    @staticmethod
    def build_from_config(config: dict) -> "_OpenAIEmbeddingFunction":
        from app.core.config import get_settings

        settings = get_settings()
        return _OpenAIEmbeddingFunction(
            api_base_url=config.get("api_base_url", settings.rag_embedding_api_base_url),
            api_key=settings.rag_embedding_api_key or "",
            model=config.get("model", settings.rag_embedding_model),
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"_OpenAIEmbeddingFunction(model={self._model!r})"


def _build_embedding_function() -> _OpenAIEmbeddingFunction | None:
    """Build an embedding function from settings, or None if key is missing."""
    from app.core.config import get_settings

    settings = get_settings()
    api_key = settings.rag_embedding_api_key
    if not api_key:
        logger.warning(
            "RAG_EMBEDDING_API_KEY not configured; "
            "collection will not have an embedding function"
        )
        return None
    return _OpenAIEmbeddingFunction(
        api_base_url=settings.rag_embedding_api_base_url,
        api_key=api_key,
        model=settings.rag_embedding_model,
    )


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

    The collection is created with an OpenAI embedding function so callers
    can use ``documents`` / ``query_texts`` without manual vectors.

    Returns None when chromadb is unavailable or embedding key is missing.
    """
    client = get_chroma_client()
    if client is None:
        return None

    ef = _build_embedding_function()
    if ef is None:
        logger.error(
            "Cannot create collection without embedding function. "
            "Set RAG_EMBEDDING_API_KEY."
        )
        return None

    return client.get_or_create_collection(
        name=COMPANY_KNOWLEDGE_COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def reset_chroma_client() -> None:
    """Reset the singleton client (useful for tests)."""
    global _chroma_client
    _chroma_client = None
