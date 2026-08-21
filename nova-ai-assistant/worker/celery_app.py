"""NOVA Celery application.

Broker and result backend: Upstash Redis (TLS — rediss://).

Start the worker from the project root (nova-ai-assistant/):
    celery -A worker worker --loglevel=info
"""
import os
import ssl
import sys

from celery import Celery
from dotenv import load_dotenv

# Load environment variables from worker/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ---------------------------------------------------------------------------
# Upstash Redis requires SSL options for rediss://
# ---------------------------------------------------------------------------
_ssl_options: dict = {}
if REDIS_URL.startswith("rediss://"):
    _ssl_options = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }

celery_app = Celery(
    "nova_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks", "worker.browser_tasks"],
)

# On Windows, billiard prefork can encounter permission errors; solo/threads pool ensures smooth execution
worker_pool_setting = "solo" if sys.platform == "win32" else "prefork"

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl=_ssl_options or None,
    redis_backend_use_ssl=_ssl_options or None,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    worker_pool=worker_pool_setting,
)

# Alias so celery -A worker worker or celery -A worker.celery_app worker works automatically
celery = celery_app
app = celery_app
