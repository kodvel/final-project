"""Embedding helpers for indexed company knowledge."""

from __future__ import annotations

_EMBEDDING_DIM = 1024  # mistral-embed output dimension


def get_embeddings_for_texts(texts: list[str]) -> list[list[float]]:
    """Return semantic embeddings for a batch of texts using Mistral mistral-embed."""
    from app.core.config import get_settings
    from mistralai.client.sdk import Mistral

    settings = get_settings()
    client = Mistral(api_key=settings.rag_mistral_api_key)
    response = client.embeddings.create(model="mistral-embed", inputs=texts)
    return [item.embedding for item in response.data]
