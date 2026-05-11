"""Thin source-processing Celery task entrypoint."""

from sqlmodel import Session

from app.db.session import engine
from app.jobs.celery_app import celery_app
from app.services import source_processing as sp

try:
    from celery import Task
except ImportError:  # pragma: no cover - exercised when Celery is not installed
    Task = object  # type: ignore[misc,assignment]


def process_source_task(source_id: int) -> dict:
    """Celery task entrypoint: process a source and generate artifacts."""
    with Session(engine) as session:
        result = sp.process_source(session, source_id)
        return {"source_id": result.id, "status": result.processing_status.value}


class SourceProcessingTask(Task):
    """Base task with retry configuration."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_kwargs = {"max_retries": 3}


if celery_app is not None:
    process_source_task = celery_app.task(
        name="source_processing.process_source",
        base=SourceProcessingTask,
    )(process_source_task)
