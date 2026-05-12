"""Embedding helpers for indexed company knowledge."""

from __future__ import annotations

import hashlib
import struct

_EMBEDDING_DIM = 384  # matches common small sentence-transformer models


def deterministic_embedding(text: str, dim: int = _EMBEDDING_DIM) -> list[float]:
    """Return a deterministic fixed-dimension embedding from *text*.

    Uses SHA-256 hashes expanded to fill *dim* floats in [-1, 1].
    No external model required — suitable for tests and dev only.
    """
    floats: list[float] = []
    idx = 0
    while len(floats) < dim:
        h = hashlib.sha256(f"{text}|chunk|{idx}".encode()).digest()
        # 8 bytes → 2 floats
        for offset in range(0, 32, 4):
            if len(floats) >= dim:
                break
            i = struct.unpack(">f", h[offset : offset + 4])[0]
            # Normalize to [-1, 1]
            floats.append(max(-1.0, min(1.0, i / abs(i) * min(abs(i) / 1e38, 1.0))))
        idx += 1
    return floats


def get_embeddings_for_texts(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a batch of texts.

    Currently uses :func:`deterministic_embedding` so that no API keys are
    needed.  A real embedding model can be swapped in later.
    """
    return [deterministic_embedding(t) for t in texts]
