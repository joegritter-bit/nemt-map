from .base_scraper import BaseScraper
import os
import time
import random

class MTMScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.username = os.getenv("MTM_USERNAME")
        self.password = os.getenv("MTM_PASSWORD")
        self.login_url = "https://mtm.mtmlink.net/pe/login"

    # NOTE: I removed start_browser() so it uses the master Invisible version from BaseScraper

    def login(self):
        print(f"   🌍 Navigating to MTM Login...")
        self.page.goto(self.login_url)
        try:
            self.page.wait_for_selector("input[name='username'], input[type='text']", timeout=30000)
            
            # Check if already logged in
            if "marketplace" in self.page.url:
                print("   ✅ Already logged in.")
                return True

            print("   🔑 Entering Credentials...")
            self.human_typing("input[type='text']", self.username)
            self.human_typing("input[type='password']", self.password)
            self.page.click("button[type='submit']")
            
            # Handle MFA if it appears
            try:
                self.page.wait_for_selector("input[id='code']", timeout=5000)
                print("   🔐 MFA Requested. Check email logic in controller.")
                return False # Let the controller handle MFA
            except:
                pass

            self.page.wait_for_url("**/pe/**", timeout=30000)
            print("   ✅ MTM Dashboard Reached.")
            
            # Save the fresh session
            self.context.storage_state(path="auth.json")
            return True
            
        except Exception as e:
            print(f"   ❌ MTM Login Failed: {e}")
            self.page.screenshot(path="mtm_login_fail.png")
            return False
