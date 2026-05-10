"""Celery application placeholder. Import this module to trigger Celery installation check."""

try:
    from celery import Celery
    celery_app = Celery("company_intelligence", broker="redis://localhost:6379/0")
except ImportError:
    celery_app = None
