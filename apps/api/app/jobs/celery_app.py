from pathlib import Path

from celery import Celery
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "company_intelligence",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["app.jobs.source_processing"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
