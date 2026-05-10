from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "spotclause",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.parse", "app.tasks.analyze", "app.tasks.compare"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
)
