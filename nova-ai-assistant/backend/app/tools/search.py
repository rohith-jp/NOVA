import json
import logging
import urllib.error
import urllib.request
from typing import List, Optional

from pydantic import BaseModel

from app.core.config import settings
from app.core.firewall import PromptInjectionBlockedError, sanitize_or_reject_external_input

logger = logging.getLogger(__name__)

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    safe: bool = True
    blocked_reason: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    error: Optional[str] = None

def perform_web_search(query: str, max_results: int = 3) -> SearchResponse:
    """
    Executes a web search using the Tavily API, normalizes results,
    and passes external content through the Prompt-Injection Firewall.
    """
    api_key = settings.TAVILY_API_KEY
    if not api_key:
        logger.error("TAVILY_API_KEY environment variable is not set.")
        return SearchResponse(query=query, results=[], error="Search API is not configured.")

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
        "max_results": max(max_results, 3) # Request at least 3 results
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10.0) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body)
    except urllib.error.HTTPError as e:
        logger.error(f"Tavily API HTTP error: {e.code} - {e.reason}")
        return SearchResponse(query=query, results=[], error=f"Search service error: HTTP {e.code}")
    except Exception as e:
        logger.error(f"Tavily API execution error: {type(e).__name__}: {str(e)}")
        return SearchResponse(query=query, results=[], error="Search service execution failed.")

    raw_results = data.get("results", [])
    normalized_results = []
    
    for item in raw_results:
        title = item.get("title", "No Title")
        url_link = item.get("url", "")
        content = item.get("content", "")
        
        # Pass external content through the prompt injection firewall
        try:
            # We sanitize the content. If malicious, it raises an error.
            sanitized_content = sanitize_or_reject_external_input(content, source="tavily_search")
            sanitized_title = sanitize_or_reject_external_input(title, source="tavily_search")
            
            normalized_results.append(
                SearchResult(
                    title=sanitized_title,
                    url=url_link,
                    content=sanitized_content,
                    safe=True
                )
            )
        except PromptInjectionBlockedError as pie:
            # We keep a record of the blocked result but remove the malicious content
            logger.warning(f"Blocked search result from {url_link}: {pie.result.reason}")
            normalized_results.append(
                SearchResult(
                    title="[BLOCKED TITLE]",
                    url=url_link,
                    content="[CONTENT BLOCKED BY FIREWALL]",
                    safe=False,
                    blocked_reason=pie.result.reason
                )
            )

    return SearchResponse(query=query, results=normalized_results)
