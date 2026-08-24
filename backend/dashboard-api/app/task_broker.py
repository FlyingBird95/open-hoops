from open_hoops.core.task_broker import TaskBroker, TaskName

from app.config import settings

__all__ = ["TaskName", "task_broker"]

task_broker = TaskBroker(settings.redis_url)
