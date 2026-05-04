"""Storage helpers for local filesystem."""

from pathlib import Path

STORAGE_ROOT = Path("storage")
UPLOADS_ROOT = STORAGE_ROOT / "uploads"


def save_upload(workspace_id: int, source_id: int, filename: str, content: bytes) -> str:
    """Save uploaded file content to local storage path.

    Returns the storage path string.
    """
    ext = Path(filename).suffix.lower().lstrip(".")
    dest = UPLOADS_ROOT / str(workspace_id) / str(source_id) / f"original.{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return str(dest)


def delete_upload(storage_path: str) -> None:
    """Delete a local uploaded file if it exists."""
    p = Path(storage_path)
    if p.exists():
        p.unlink()
