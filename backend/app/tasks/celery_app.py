"""
CyberTrace AI – Celery async task queue
Handles heavy background jobs: evidence processing,
batch correlation, campaign detection.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "cybertrace",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.tasks.process_complaint_task": {"queue": "complaint_processing"},
        "app.tasks.tasks.process_evidence_task":  {"queue": "evidence_processing"},
        "app.tasks.tasks.detect_campaigns_task":  {"queue": "intelligence"},
    },
    beat_schedule={
        "detect-campaigns-every-hour": {
            "task": "app.tasks.tasks.detect_campaigns_task",
            "schedule": 3600.0,
        },
    },
)
