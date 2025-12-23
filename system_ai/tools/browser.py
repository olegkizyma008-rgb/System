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

    def get_page(self, headless: Optional[bool] = None) -> Page:
        log_file = os.path.expanduser("~/.system_cli/logs/browser_debug.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"{time.ctime()}: get_page called with headless={headless} (last={self._last_headless})\n")

        # If headless mode is not specified, use the last one or default to True
        if headless is None:
            headless = self._last_headless if self._last_headless is not None else True

        # If already running but in different headless mode, restart
        if self.pw and self.browser and self._last_headless is not None and self._last_headless != headless:
            with open(log_file, "a") as f:
                f.write(f"{time.ctime()}: Re-starting browser due to headless change\n")
            self.close()

        if not self.browser:
            with open(log_file, "a") as f:
                f.write(f"{time.ctime()}: Launching new browser instance\n")
            try:
                if not self.pw:
                    self.pw = sync_playwright().start()
                
                self._last_headless = headless
                
                # Try to connect to existing Chrome via CDP first
                cdp_url = os.environ.get("CHROME_CDP_URL", "http://127.0.0.1:9222")
                try:
                    self.browser = self.pw.chromium.connect_over_cdp(cdp_url)
                    # Get the first page or create one
                    pages = self.browser.contexts[0].pages if self.browser.contexts else []
                    if pages:
                        self.page = pages[0]
                    else:
                        self.page = self.browser.contexts[0].new_page() if self.browser.contexts else self.browser.new_context().new_page()
                    self._connected_via_cdp = True
                    return self.page
                except Exception:
                    # CDP connection failed, fall back to launching new browser
                    self._connected_via_cdp = False
                
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
            except Exception:
                # If launch fails, ensure we cleanup to allow fresh retry
                self.close()
                raise

        return self.page


    def close(self):
        log_file = os.path.expanduser("~/.system_cli/logs/browser_debug.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"{time.ctime()}: close() called\n")
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        if self.pw:
            try:
                self.pw.stop()
            except Exception:
                pass
        self.pw = None
        self.browser = None
        self.page = None

def browser_open_url(url: str, headless: bool = False) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page(headless=headless)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2) # Give page some time to settle
        
        content = page.content().lower()
        captcha_markers = [
            "g-recaptcha", "hcaptcha", "cloudflare-turnstile",
            "verify you are human", "solving this captcha",
            "unusual traffic from your computer network",
            "check if you are a robot"
        ]
        has_captcha = any(marker in content for marker in captcha_markers)
        if not has_captcha and ("sorry" in content and "unusual traffic" in content):
            has_captcha = True
        
        if has_captcha:
            return json.dumps({
                "status": "captcha",
                "error": "CAPTCHA detected - blocked by Google. Use DuckDuckGo instead.",
                "url": page.url,
                "has_captcha": True
            }, ensure_ascii=False)
        return json.dumps({
            "status": "success",
            "url": page.url,
            "title": page.title(),
            "has_captcha": False
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_click_element(selector: str) -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        page.click(selector, timeout=5000)
        try:
             page.wait_for_load_state("domcontentloaded", timeout=5000)
             time.sleep(1.0)
        except Exception:
             time.sleep(1.0)
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_type_text(selector: str, text: str, press_enter: bool = False) -> str:
    try:
        if selector == "input[name='q']" or selector == 'input[name="q"]':
            selector = 'textarea[name="q"]'
            
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        page.fill(selector, text, timeout=10000)
        if press_enter:
            page.press(selector, "Enter")
            try:
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                time.sleep(2.0)
            except Exception:
                time.sleep(3.0)
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
            project_dir = os.path.abspath(".agent/workflows/data/screenshots")
            if os.path.isdir(project_dir):
                output_dir = project_dir
            else:
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
        text_content = page.inner_text("body")
        return json.dumps({
            "status": "success",
            "content": text_content[:15000],
            "url": page.url,
            "title": page.title()
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_snapshot() -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        content = page.content()
        content_lower = content.lower()
        captcha_markers = [
            "g-recaptcha", "hcaptcha", "cloudflare-turnstile",
            "verify you are human", "solving this captcha",
            "unusual traffic from your computer network",
            "check if you are a robot"
        ]
        has_captcha = any(marker in content_lower for marker in captcha_markers)
        if not has_captcha and ("sorry" in content_lower and "unusual traffic" in content_lower):
            has_captcha = True
        
        return json.dumps({
            "status": "success",
            "url": page.url,
            "title": page.title(),
            "has_captcha": has_captcha,
            "content_preview": content[:30000]
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_navigate(url: str, headless: bool = False) -> str:
    return browser_open_url(url, headless=headless)

def browser_get_links() -> str:
    try:
        manager = BrowserManager.get_instance()
        page = manager.get_page()
        
        # Check if currently on a captcha/sorry page
        current_url = page.url.lower()
        content = page.content().lower()
        captcha_indicators = ["sorry/index", "recaptcha", "unusual traffic", "captcha"]
        if any(ind in current_url or ind in content for ind in captcha_indicators):
            return json.dumps({
                "status": "captcha",
                "error": "Currently on CAPTCHA page - cannot get links. Use DuckDuckGo instead.",
                "links": []
            }, ensure_ascii=False)
        
        links = page.evaluate("""
            () => {
                const results = [];
                const anchors = document.querySelectorAll('a[href]');
                anchors.forEach(a => {
                    const text = a.innerText.trim();
                    const href = a.href;
                    if (text && href && !href.startsWith('javascript:')) {
                        results.push({text, href});
                    }
                });
                return results;
            }
        """)
        
        # Warn if no links found (possible blocked page)
        if not links:
            return json.dumps({
                "status": "warning",
                "message": "No links found - page may be blocked or empty",
                "links": []
            }, ensure_ascii=False)
        
        return json.dumps({"status": "success", "links": links[:50]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

def browser_close() -> str:
    try:
        BrowserManager.get_instance().close()
        return json.dumps({"status": "success"})
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


def browser_search_duckduckgo(query: str, headless: bool = False) -> str:
    """Search using DuckDuckGo - CAPTCHA-resistant alternative to Google.
    
    Args:
        query: Search query string
        headless: Whether to run browser in headless mode
        
    Returns:
        JSON with status, links found, and any errors
    """
    try:
        import urllib.parse
        manager = BrowserManager.get_instance()
        page = manager.get_page(headless=headless)
        
        # DuckDuckGo search URL
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://duckduckgo.com/?q={encoded_query}"
        
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(2)  # Wait for results to load
        
        # Extract search result links
        links = page.evaluate("""
            () => {
                const results = [];
                // DuckDuckGo result links are in data-testid="result" or class="result__a"
                const anchors = document.querySelectorAll('a[data-testid="result-title-a"], a.result__a, article a');
                anchors.forEach(a => {
                    const text = a.innerText.trim();
                    const href = a.href;
                    if (text && href && !href.includes('duckduckgo.com') && !href.startsWith('javascript:')) {
                        results.push({text, href});
                    }
                });
                return results;
            }
        """)
        
        return json.dumps({
            "status": "success",
            "url": page.url,
            "query": query,
            "links": links[:30],  # Top 30 results
            "source": "duckduckgo"
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

