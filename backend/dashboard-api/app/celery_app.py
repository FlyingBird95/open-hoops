from celery import Celery

from app.config import settings

celery = Celery("open_hoops", broker=settings.redis_url)
