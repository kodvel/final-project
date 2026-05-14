"""Thin source-processing Celery task entrypoint."""

from sqlmodel import Session

from app.db.session import engine
from app.jobs.celery_app import celery_app
from app.services import source_processing as sp

def process_source_task(source_id: int) -> dict:
    """Celery task entrypoint: process a source and generate artifacts."""
    with Session(engine) as session:
        result = sp.process_source(session, source_id)
        return {"source_id": result.id, "status": result.processing_status.value}


if celery_app is not None:
    process_source_task = celery_app.task(
        name="source_processing.process_source",
    )(process_source_task)
