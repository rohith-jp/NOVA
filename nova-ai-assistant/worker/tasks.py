"""NOVA Celery tasks.

All tasks in this module are automatically registered with the Celery app
via the `include=["worker.tasks"]` directive in celery_app.py.

Do not add browser automation, Claude, or agent tasks here yet.
"""
import time

from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.ping", bind=True)
def ping(self) -> dict:
    """Trivial health-check task.

    Returns a simple success payload so that we can verify:
      1. The worker starts and connects to Upstash Redis.
      2. A task can be dispatched and its result retrieved.

    Usage:
        from worker.tasks import ping
        result = ping.delay()
        print(result.get(timeout=10))
    """
    return {
        "status": "pong",
        "task_id": self.request.id,
        "timestamp": time.time(),
    }
