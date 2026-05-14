"""Helpers for creating an OpenAI client with optional Langfuse tracing."""

from typing import Any


def create_openai_client(**kwargs: Any):
    """Create an OpenAI client, preferring Langfuse wrapper when available."""
    try:
        from langfuse.openai import OpenAI

        return OpenAI(**kwargs)
    except Exception:
        from openai import OpenAI

        return OpenAI(**kwargs)
