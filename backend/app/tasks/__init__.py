"""Shared Celery application instance.

Phase 2 pipeline tasks (transcription, moment analysis, rendering) register
against this instance via `@celery_app.task`. Long-running video work must
never run inline in a FastAPI request handler - see CLAUDE.md.

Run the worker with:
    celery -A app.tasks worker --loglevel=info
"""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "ai_video_slicer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    # `celery -A app.tasks worker` only imports this __init__.py to obtain
    # celery_app - it never imports app.tasks.pipeline on its own, so the
    # @celery_app.task-decorated functions there would never register and
    # every dispatched job would sit at "pending" forever with no error.
    # `include` forces Celery to import it during worker startup.
    include=["app.tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
