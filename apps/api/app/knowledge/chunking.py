"""Document chunking helpers for company knowledge retrieval."""


def chunk_markdown(markdown: str, chunk_size: int = 3000, min_chars: int = 300) -> list[str]:
    """Chunk markdown text using Chonkie RecursiveChunker."""
    from chonkie import RecursiveChunker

    chunker = RecursiveChunker(tokenizer="character", chunk_size=chunk_size, min_characters_per_chunk=min_chars)
    chunks = chunker.chunk(markdown)
    return [chunk.text for chunk in chunks]
