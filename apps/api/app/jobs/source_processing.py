"""Thin source-processing Celery task entrypoint."""

from celery import Task

from app.db.session import SessionLocal
from app.services import source_processing as sp


def process_source_task(source_id: int) -> dict:
    """Celery task entrypoint: process a source and generate artifacts."""
    with SessionLocal() as session:
        result = sp.process_source(session, source_id)
        return {"source_id": result.id, "status": result.processing_status.value}


class SourceProcessingTask(Task):
    """Base task with retry configuration."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_kwargs = {"max_retries": 3}


# Bind to celery app instance in jobs/celery_app.py
# This file stays thin; all testable logic is in services/source_processing.py
