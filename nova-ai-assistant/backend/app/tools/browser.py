import logging
import os
from typing import Optional
from pydantic import BaseModel
from celery import Celery

from app.core.firewall import sanitize_or_reject_external_input, PromptInjectionBlockedError

logger = logging.getLogger(__name__)

# Initialize a Celery client to communicate with the worker
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
celery_client = Celery("nova_client", broker=redis_url, backend=redis_url)

class BrowserResult(BaseModel):
    url: str
    title: str
    content: str
    safe: bool = True
    blocked_reason: Optional[str] = None
    error: Optional[str] = None

def read_webpage_safely(url: str, timeout_ms: int = 15000) -> BrowserResult:
    """
    Submits a browser task to Celery to fetch the page content, waits for the result,
    and passes the extracted text through the prompt-injection firewall.
    """
    try:
        # Send task to Celery worker synchronously waiting for result
        async_result = celery_client.send_task(
            "browser.fetch_page_content",
            args=[url],
            kwargs={"timeout_ms": timeout_ms}
        )
        # Wait slightly longer than the browser timeout
        task_result = async_result.get(timeout=(timeout_ms / 1000.0) + 5.0)
    except Exception as e:
        logger.error(f"Failed to communicate with browser worker: {e}")
        return BrowserResult(url=url, title="", content="", error=f"Worker communication failed: {e}")
        
    if task_result.get("error"):
        return BrowserResult(
            url=task_result["url"],
            title=task_result.get("title", ""),
            content="",
            error=task_result["error"]
        )
        
    raw_title = task_result.get("title", "")
    raw_content = task_result.get("content", "")
    
    # -------------------------------------------------------------
    # Pass external text through the prompt-injection firewall
    # -------------------------------------------------------------
    try:
        sanitized_content = sanitize_or_reject_external_input(raw_content, source="browser_automation")
        sanitized_title = sanitize_or_reject_external_input(raw_title, source="browser_automation")
        
        return BrowserResult(
            url=task_result["url"],
            title=sanitized_title,
            content=sanitized_content,
            safe=True
        )
    except PromptInjectionBlockedError as pie:
        logger.warning(f"Blocked malicious browser content from {url}: {pie.result.reason}")
        return BrowserResult(
            url=task_result["url"],
            title="[BLOCKED TITLE]",
            content="[CONTENT BLOCKED BY FIREWALL]",
            safe=False,
            blocked_reason=pie.result.reason
        )
