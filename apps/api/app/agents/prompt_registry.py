"""Fetch prompts from Langfuse with safe in-code fallbacks.

Each LLM call site asks for a prompt by its Langfuse name. When Langfuse
credentials are unset or a fetch fails, the bundled fallback string is used
so tests, CI, and offline development continue to work.

The returned ``LoadedPrompt`` exposes:
- ``text``: compiled prompt content ready to pass to the LLM
- ``langfuse_prompt``: the underlying Langfuse prompt object (or ``None``);
  pass it as ``langfuse_prompt=`` to ``langfuse.openai`` calls to link
  generations back to the prompt version in the Langfuse UI.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedPrompt:
    """Compiled prompt text plus optional Langfuse prompt object for trace linking."""

    text: str
    langfuse_prompt: Any | None = None


def _format_fallback(template: str, variables: dict[str, Any]) -> str:
    """Apply Python ``str.format`` if variables provided, else return as-is."""
    if not variables:
        return template
    return template.format(**variables)


@lru_cache(maxsize=1)
def _get_langfuse_client():
    """Return a cached Langfuse client initialized from app settings.

    Uses explicit credentials from Settings rather than get_client(), which
    reads from os.environ and misses values loaded only via pydantic .env parsing.
    """
    from langfuse import Langfuse

    settings = get_settings()
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def load_prompt(
    name: str,
    fallback: str,
    label: str = "production",
    **variables: Any,
) -> LoadedPrompt:
    """Fetch a Langfuse text prompt by ``name`` at ``label``, with fallback."""
    settings = get_settings()
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return LoadedPrompt(text=_format_fallback(fallback, variables))

    try:
        client = _get_langfuse_client()
        prompt = client.get_prompt(name, label=label)
        compiled = prompt.compile(**variables) if variables else prompt.prompt
        return LoadedPrompt(text=compiled, langfuse_prompt=prompt)
    except Exception:
        logger.warning(
            "Failed to fetch Langfuse prompt %r (label=%s); using in-code fallback",
            name,
            label,
            exc_info=True,
        )
        return LoadedPrompt(text=_format_fallback(fallback, variables))
