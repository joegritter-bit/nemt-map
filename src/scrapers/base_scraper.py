from playwright.sync_api import sync_playwright
import os
import time

class BaseScraper:
    def __init__(self):
        self.page = None
        self.browser = None
        self.context = None
        self.p = None

    def start_browser(self, headless=True, auth_file=None):
        """
        Launches the browser in INVISIBLE (Headless) mode with stealth settings.
        """
        print("   🚀 Launching Chrome (Invisible Stealth Mode)...")
        self.p = sync_playwright().start()
        
        # ARGS:
        # --disable-blink-features=AutomationControlled : Hides the "I am a robot" flag
        # --no-sandbox : Required for stable Linux execution
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1280,800"
        ]

        # Force Headless = True (No window will open)
        self.browser = self.p.chromium.launch(
            headless=True,
            args=launch_args
        )

        # Context: Set a real User-Agent so Modivcare thinks we are human
        context_args = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        
        # Load saved session (MTM MFA)
        if auth_file and os.path.exists(auth_file):
            print(f"   🍪 Loading session from {auth_file}...")
            context_args["storage_state"] = auth_file

        self.context = self.browser.new_context(**context_args)
        self.page = self.context.new_page()

    def close_browser(self):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.p:
            self.p.stop()
        print("   💤 Browser closed.")

    def human_typing(self, selector, text, delay=0.1):
        self.page.type(selector, text, delay=delay * 1000)
