from sqlmodel import Session

import app.db.base  # noqa: F401 — registers all SQLAlchemy models so FK resolution works in the worker
from app.db.session import engine
from app.jobs.celery_app import celery_app
from app.services import source_processing as sp


@celery_app.task(name="source_processing.process_source")
def process_source_task(source_id: int) -> dict:
    """Celery task: process a source and generate artifacts."""
    with Session(engine) as session:
        result = sp.process_source(session, source_id)
        return {"source_id": result.id, "status": result.processing_status.value}
