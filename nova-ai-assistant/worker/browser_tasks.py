import logging
from typing import Dict, Any
from celery import shared_task
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

@shared_task(name="browser.fetch_page_content", bind=True)
def fetch_page_content(self, url: str, timeout_ms: int = 15000) -> Dict[str, Any]:
    """
    Safely navigates to a URL, waits for it to load, and extracts the visible text content.
    Returns structured dict containing title, url, content, or error.
    """
    logger.info(f"Browser Task starting fetch for: {url}")
    
    result: Dict[str, Any] = {
        "url": url,
        "title": "",
        "content": "",
        "error": None
    }
    
    try:
        with sync_playwright() as p:
            # Launch Chromium headless
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 NOVA-Assistant",
                viewport={"width": 1280, "height": 720}
            )
            page = context.new_page()
            
            try:
                # Navigate with safe timeout
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                
                # Extract basic title
                result["title"] = page.title()
                
                # Extract inner text of the body, removing excess whitespace
                content = page.locator("body").inner_text(timeout=5000)
                if content:
                    # Basic normalization
                    lines = (line.strip() for line in content.splitlines())
                    result["content"] = "\n".join(line for line in lines if line)
                
            except PlaywrightTimeoutError:
                logger.warning(f"Timeout while fetching {url}")
                result["error"] = "Timeout exceeded while navigating or loading page."
            except Exception as e:
                logger.error(f"Browser navigation exception for {url}: {str(e)}")
                result["error"] = f"Failed to load or parse page: {str(e)}"
            finally:
                browser.close()
                
    except Exception as e:
        logger.error(f"Browser engine exception for {url}: {str(e)}")
        result["error"] = f"Failed to initialize browser: {str(e)}"
        
    return result
