import worker.tasks  # noqa: F401 — triggers task registration
from worker.celery_app import celery

from open_hoops.core.task_broker import TaskName


def test_all_task_names_registered_in_worker():
    registered = set(celery.tasks.keys())
    for task_name in TaskName:
        assert task_name.value in registered, f"{task_name.value} not registered in worker"
