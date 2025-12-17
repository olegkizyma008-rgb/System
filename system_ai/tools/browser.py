"""Browser Tools Module

Provides tools for advanced browser automation using Playwright.
Maintains a persistent browser session for multi-step interactions.
"""

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from typing import Dict, Any, Optional
import time

class BrowserManager:
    _instance = None
    _playwright = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, headless: bool = False):
        if not self._playwright:
            self._playwright = sync_playwright().start()
        
        if not self._browser:
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()

    def get_page(self) -> Page:
        self.start()
        return self._page

    def stop(self):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        
        self._context = None
        self._browser = None
        self._playwright = None
        self._page = None

# Global manager instance
_manager = BrowserManager.get_instance()

def browser_open_url(url: str, headless: bool = False) -> Dict[str, Any]:
    """Open a URL in the browser
    
    Args:
        url: URL to open
        headless: Whether to run invisible (default False for user visibility)
        
    Returns:
        Dict with status and title
    """
    try:
        # Force headless=False if user wants to see it, updating session if needed
        # For simplicity, we just ensure it's started. Restarting with diff config is complex.
        _manager.start(headless=headless) 
        page = _manager.get_page()
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        
        return {
            "tool": "browser_open_url",
            "status": "success",
            "title": page.title(),
            "url": page.url
        }
    except Exception as e:
        return {
            "tool": "browser_open_url",
            "status": "error",
            "error": str(e)
        }

def browser_click_element(selector: str) -> Dict[str, Any]:
    """Click an element on the current page
    
    Args:
        selector: CSS or XPath selector
        
    Returns:
        Dict with status
    """
    try:
        page = _manager.get_page()
        page.click(selector)
        return {
            "tool": "browser_click_element",
            "status": "success",
            "selector": selector
        }
    except Exception as e:
        return {
            "tool": "browser_click_element",
            "status": "error",
            "error": str(e)
        }

def browser_type_text(selector: str, text: str) -> Dict[str, Any]:
    """Type text into an element
    
    Args:
        selector: CSS or XPath selector
        text: Text to type
        
    Returns:
        Dict with status
    """
    try:
        page = _manager.get_page()
        page.fill(selector, text)
        return {
            "tool": "browser_type_text",
            "status": "success",
            "selector": selector,
            "text_length": len(text)
        }
    except Exception as e:
        return {
            "tool": "browser_type_text",
            "status": "error",
            "error": str(e)
        }

def browser_get_content(selector: Optional[str] = None) -> Dict[str, Any]:
    """Get content of the page or specific element
    
    Args:
        selector: Optional selector to get text from. If None, gets full page text.
        
    Returns:
        Dict with status and content
    """
    try:
        page = _manager.get_page()
        content = ""
        if selector:
            content = page.inner_text(selector)
        else:
            # Get readable content or body text
            content = page.evaluate("document.body.innerText")
            
        return {
            "tool": "browser_get_content",
            "status": "success",
            "content": content[:5000], # Trucate for safety
            "length": len(content)
        }
    except Exception as e:
        return {
            "tool": "browser_get_content",
            "status": "error",
            "error": str(e)
        }

def browser_execute_script(script: str) -> Dict[str, Any]:
    """Execute JavaScript on the page
    
    Args:
        script: JS code to execute
        
    Returns:
        Dict with status and result
    """
    try:
        page = _manager.get_page()
        result = page.evaluate(script)
        return {
            "tool": "browser_execute_script",
            "status": "success",
            "result": str(result)
        }
    except Exception as e:
        return {
            "tool": "browser_execute_script",
            "status": "error",
            "error": str(e)
        }
