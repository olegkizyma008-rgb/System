import os
import time
import json
from typing import Optional, Dict, List, Any
from playwright.sync_api import sync_playwright, Browser, Page

class BrowserManager:
    _instance = None
    
    def __init__(self):
        self.pw = None
        self.browser = None
        self.page: Optional[Page] = None
        self._last_headless = None
        self.user_data_dir = os.path.expanduser("~/.antigravity/browser_session")
        os.makedirs(self.user_data_dir, exist_ok=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_page(self, headless: bool = True) -> Page:
        # If already running but in different headless mode, restart
        if self.pw and self.browser and self._last_headless != headless:
            self.close()

        if not self.pw:
            self.pw = sync_playwright().start()
            self._last_headless = headless
            
            # Chromium args
            args = ["--disable-blink-features=AutomationControlled"]
            # Only add sandbox flags if not on macOS (to avoid warning banner)
            import platform
            if platform.system() != "Darwin":
                args.extend(["--no-sandbox", "--disable-setuid-sandbox"])
            
            self.browser = self.pw.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                args=args,
                viewport={"width": 1280, "height": 720}
            )
            self.page = self.browser.pages[0]
        return self.page

    def close(self):
        if self.browser:
            self.browser.close()
        if self.pw:
            self.pw.stop()
        self.pw = None
        self.browser = None
        self.page = None

def browser_open_url(url: str, headless: bool = True) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page(headless=headless)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        content = page.content().lower()
        has_captcha = "sorry" in content or "captcha" in content or "robot" in content
        
        return json.dumps({
            "status": "success",
            "url": page.url,
            "title": page.title(),
            "has_captcha": has_captcha
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_click_element(selector: str) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        page.click(selector, timeout=5000)
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_type_text(selector: str, text: str, press_enter: bool = False) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        page.fill(selector, text, timeout=5000)
        if press_enter:
            page.press(selector, "Enter")
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_press_key(key: str) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        page.keyboard.press(key)
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_execute_script(script: str) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        result = page.evaluate(script)
        return json.dumps({"status": "success", "result": str(result)})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_ensure_ready() -> str:
    try:
        manager = BrowserManager.get_instance()
        manager.get_page()
        return json.dumps({"status": "success", "message": "Browser is ready"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_screenshot(path: Optional[str] = None) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        if not path:
            output_dir = os.path.expanduser("~/.antigravity/vision_cache")
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"browser_{int(time.time())}.png")
        page.screenshot(path=path)
        return json.dumps({"status": "success", "path": path})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_get_content() -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        return json.dumps({
            "status": "success",
            "content": page.content()[:5000],
            "url": page.url,
            "title": page.title()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_snapshot() -> str:
    """Capture accessibility snapshot of the current page.
    Note: Full A11y tree snapshot was removed in v1.50+. 
    This tool now returns a simplified view with content, url, and title.
    """
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        content = page.content()
        
        # Basic CAPTCHA check
        has_captcha = "sorry" in content.lower() or "captcha" in content.lower() or "robot" in content.lower()
        
        return json.dumps({
            "status": "success",
            "url": page.url,
            "title": page.title(),
            "has_captcha": has_captcha,
            "content_preview": content[:10000] # Return more content for verification
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_navigate(url: str, headless: bool = True) -> str:
    """Alias for browser_open_url."""
    return browser_open_url(url, headless=headless)

def browser_close() -> str:
    try:
        BrowserManager.get_instance().close()
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
