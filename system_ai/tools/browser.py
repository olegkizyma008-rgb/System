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

    def _ensure_page_valid(self):
        """Check if page is still open and valid, recreate if needed."""
        try:
            if self._page and not self._page.is_closed():
                return True
        except Exception:
            pass
        
        if self._context and not self._context.pages:
            self._page = self._context.new_page()
            return True
        elif self._context and self._context.pages:
            self._page = self._context.pages[0]
            return True
        
        # If everything is gone, restart
        self.start()
        return True

    def start(self, headless: bool = False):
        if not self._playwright:
            self._playwright = sync_playwright().start()
        
        if not self._browser:
            try:
                # Use a more stable launch configuration
                self._browser = self._playwright.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    raise Exception(f"Browser executables not found. Please run 'playwright install chromium' in the terminal. Original error: {e}")
                raise e
            self._context = self._browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="uk-UA",
                timezone_id="Europe/Kyiv",
                color_scheme="dark"
            )
            self._page = self._context.new_page()
            # Store current mode
            self._current_headless = headless
        else:
            # If already started, check if mode changed
            if hasattr(self, '_current_headless') and self._current_headless != headless:
                print(f"[BrowserManager] Switching headless mode: {self._current_headless} -> {headless}. Restarting...")
                self.stop()
                self.start(headless=headless)
            else:
                # Just ensure we have a page
                self._ensure_page_valid()

    def get_page(self) -> Page:
        self.start()
        self._ensure_page_valid()
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

def browser_ensure_ready() -> Dict[str, Any]:
    """Check if browser is ready, with setup instructions if not.
    
    Returns:
        Dict with status and fix_command if Playwright not installed
    """
    try:
        # Try to start browser (will raise exception if not installed)
        _manager.start(headless=True)
        # If successful, close it
        _manager.stop()
        return {
            "tool": "browser_ensure_ready",
            "status": "success",
            "message": "Browser is ready to use"
        }
    except Exception as e:
        error_msg = str(e)
        if "Executable doesn't exist" in error_msg or "not found" in error_msg.lower():
            return {
                "tool": "browser_ensure_ready",
                "status": "error",
                "error_type": "dependency_missing",
                "message": "Playwright browsers not installed",
                "fix_command": "playwright install chromium",
                "error": error_msg
            }
        return {
            "tool": "browser_ensure_ready",
            "status": "error",
            "error": error_msg
        }


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
        
        # Human-like delay
        import random
        time.sleep(random.uniform(0.5, 1.5))
        
        # Use networkidle for better reliability on heavy sites
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_load_state("networkidle")
        
        # Anti-bot detection: Google "Sorry" page
        title = page.title()
        content = page.content().lower()
        if "google.com/sorry" in page.url or "unusual traffic" in content:
            return {
                "tool": "browser_open_url",
                "status": "error",
                "error": "Google detected bot traffic (CAPTCHA/Sorry page). Switch to another search engine or use Native GUI.",
                "url": page.url
            }
            
        return {
            "tool": "browser_open_url",
            "status": "success",
            "title": title,
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
        import random
        page = _manager.get_page()
        
        # Human-like mouse movement (jitter) before hover/click
        box = page.locator(selector).bounding_box()
        if box:
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            # Move mouse in small steps with jitter
            for _ in range(3):
                page.mouse.move(x + random.uniform(-5, 5), y + random.uniform(-5, 5))
                time.sleep(random.uniform(0.05, 0.1))
        
        # Hover before click to trigger scripts/styles
        page.hover(selector)
        time.sleep(random.uniform(0.3, 0.7))
        
        # Random scroll before click
        if random.random() > 0.7:
             page.evaluate("window.scrollBy(0, window.innerHeight * 0.3)")
             time.sleep(random.uniform(0.5, 1.0))
             page.hover(selector) # Re-hover after scroll
        
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

def browser_type_text(selector: str, text: str, press_enter: bool = False) -> Dict[str, Any]:
    """Type text into an element
    
    Args:
        selector: CSS or XPath selector
        text: Text to type
        press_enter: Whether to press Enter after typing (default False)
        
    Returns:
        Dict with status
    """
    try:
        import random
        page = _manager.get_page()
        # Ensure focus first
        page.focus(selector)
        time.sleep(random.uniform(0.1, 0.3))
        
        # Clear existing text if any and type character by character with random delays
        page.fill(selector, "")
        for char in text:
            page.type(selector, char)
            time.sleep(random.uniform(0.02, 0.12))
        
        if press_enter:
            page.press(selector, "Enter")
            
        return {
            "tool": "browser_type_text",
            "status": "success",
            "selector": selector,
            "text_length": len(text),
            "pressed_enter": press_enter
        }
    except Exception as e:
        return {
            "tool": "browser_type_text",
            "status": "error",
            "error": str(e)
        }

def browser_press_key(key: str, selector: Optional[str] = None) -> Dict[str, Any]:
    """Press a key (Enter, Escape, ArrowDown, etc.)
    
    Args:
        key: Key name (e.g., 'Enter', 'Escape', 'Tab', 'ArrowDown')
        selector: Optional selector to target the keypress. If None, presses on global page.
        
    Returns:
        Dict with status
    """
    try:
        page = _manager.get_page()
        if selector:
            page.press(selector, key)
        else:
            page.keyboard.press(key)
            
        return {
            "tool": "browser_press_key",
            "status": "success",
            "key": key,
            "selector": selector
        }
    except Exception as e:
        return {
            "tool": "browser_press_key",
            "status": "error",
            "error": str(e)
        }

def browser_screenshot(path: Optional[str] = None) -> Dict[str, Any]:
    """Take a screenshot of the current browser page
    
    Args:
        path: Optional path to save. If None, saves to vision_cache.
        
    Returns:
        Dict with status and file path
    """
    try:
        import os
        from datetime import datetime
        
        page = _manager.get_page()
        
        if not path:
            cache_dir = os.path.expanduser("~/.antigravity/vision_cache")
            os.makedirs(cache_dir, exist_ok=True)
            filename = f"browser_{int(datetime.now().timestamp())}.png"
            path = os.path.join(cache_dir, filename)
            
        page.screenshot(path=path, full_page=False)
        
        return {
            "tool": "browser_screenshot",
            "status": "success",
            "path": path
        }
    except Exception as e:
        return {
            "tool": "browser_screenshot",
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
