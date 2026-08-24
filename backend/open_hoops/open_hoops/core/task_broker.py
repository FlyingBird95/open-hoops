import json
import uuid
from base64 import b64encode
from enum import StrEnum

import redis


class TaskName(StrEnum):
    ANALYZE_GAME = "worker.tasks.analyze_game"


class TaskBroker:
    def __init__(self, redis_url: str):
        self._redis = redis.Redis.from_url(redis_url)

    def send(self, task_name: TaskName, args: list, queue: str = "analysis") -> str:
        task_id = str(uuid.uuid4())
        body = b64encode(
            json.dumps(
                [args, {}, {"callbacks": None, "errbacks": None, "chain": None, "chord": None}]
            ).encode()
        ).decode()

        message = json.dumps({
            "body": body,
            "content-encoding": "utf-8",
            "content-type": "application/json",
            "headers": {
                "lang": "py",
                "task": task_name,
                "id": task_id,
                "shadow": None,
                "eta": None,
                "expires": None,
                "group": None,
                "group_index": None,
                "retries": 0,
                "timelimit": [None, None],
                "root_id": task_id,
                "parent_id": None,
                "argsrepr": repr(tuple(args)),
                "kwargsrepr": "{}",
                "origin": "dashboard-api",
            },
            "properties": {
                "correlation_id": task_id,
                "reply_to": str(uuid.uuid4()),
                "delivery_mode": 2,
                "delivery_info": {"exchange": "", "routing_key": queue},
                "priority": 0,
                "body_encoding": "base64",
                "delivery_tag": str(uuid.uuid4()),
            },
        })

        self._redis.lpush(queue, message)
        return task_id
