from playwright.sync_api import sync_playwright
import os
import time
import random
from dotenv import load_dotenv

load_dotenv(override=True)

USERNAME = os.getenv("MODIVCARE_USER")
PASSWORD = os.getenv("MODIVCARE_PASS")
LOGIN_URL = "https://transportationco.logisticare.com/Login.aspx"

def human_wiggle(page):
    try:
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y, steps=random.randint(10, 25))
            time.sleep(random.uniform(0.1, 0.4))
    except:
        pass

def human_type(page, text):
    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.2))

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"🌍 Navigating to {LOGIN_URL}...")
        page.goto(LOGIN_URL)
        page.wait_for_load_state("domcontentloaded")
        
        # --- LOGIN ---
        print("🔑 Logging in...")
        human_wiggle(page)
        human_type(page, USERNAME)
        page.keyboard.press("Tab")
        time.sleep(0.5)
        human_type(page, PASSWORD)
        time.sleep(1)
        page.keyboard.press("Enter")
        
        # Wait for Dashboard
        print("⏳ Waiting for Dashboard...")
        page.wait_for_url("**/Home.aspx**", timeout=30000)
        print("   ✅ Dashboard reached.")
        time.sleep(3)

        # --- FIND & CLICK MARKETPLACE ---
        print("\n🔎 Looking for 'Market' link...")
        
        # We start a "Popup Listener" in case it opens a new tab
        with context.expect_page() as new_page_info:
            clicked = False
            
            # Try 1: Exact text "Market"
            try:
                link = page.locator("a:has-text('Market')").first
                if link.is_visible():
                    print("   👉 Found 'Market' link. Clicking...")
                    human_wiggle(page)
                    link.click()
                    clicked = True
            except:
                pass

            # Try 2: If "Market" failed, try "Marketplace"
            if not clicked:
                try:
                    link = page.locator("a:has-text('Marketplace')").first
                    if link.is_visible():
                        print("   👉 Found 'Marketplace' link. Clicking...")
                        human_wiggle(page)
                        link.click()
                        clicked = True
                except:
                    pass

            if not clicked:
                print("   ❌ Could not find Market link. Dumping all links to debug...")
                links = page.query_selector_all("a")
                for l in links:
                    print(f"   Link: {l.inner_text()}")
                return

        # --- HANDLE THE NEW PAGE ---
        print("⏳ Waiting for Marketplace tab to open...")
        market_page = new_page_info.value
        market_page.wait_for_load_state("domcontentloaded")
        print(f"   ✅ New Tab Opened: {market_page.url}")
        
        time.sleep(5) # Let the heavy table load

        # --- DUMP DATA ---
        print("\n📊 CHECKING TABLE HEADERS:")
        try:
            market_page.wait_for_selector("th, div[role='columnheader']", timeout=15000)
            headers = market_page.query_selector_all("th")
            if not headers:
                headers = market_page.query_selector_all("div[role='columnheader']")
            
            for i, h in enumerate(headers):
                print(f"   Col {i}: {h.inner_text().strip()}")
        except:
            print("   ⚠️ Timed out waiting for headers.")

        # --- SNAPSHOT ---
        print("\n📸 Taking screenshot of Marketplace...")
        market_page.screenshot(path="modivcare_success.png")
        
        print("😴 Closing in 10 seconds...")
        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    run()
