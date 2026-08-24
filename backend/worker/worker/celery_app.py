import os
import sys

from celery import Celery

redis_url = os.environ.get("OPEN_HOOPS_REDIS_URL", "redis://localhost:6379/0")

celery = Celery("open_hoops", broker=redis_url)
celery.conf.task_routes = {"worker.tasks.*": {"queue": "analysis"}}
if sys.platform == "darwin":
    celery.conf.worker_pool = "solo"
celery.autodiscover_tasks(["worker"])
