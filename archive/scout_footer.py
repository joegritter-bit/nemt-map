from playwright.sync_api import sync_playwright
import os
import time
from dotenv import load_dotenv

load_dotenv(override=True)

USERNAME = os.getenv("MODIVCARE_USER")
PASSWORD = os.getenv("MODIVCARE_PASS")
LOGIN_URL = "https://transportationco.logisticare.com/Login.aspx"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"🌍 Navigating to {LOGIN_URL}...")
        page.goto(LOGIN_URL)
        page.wait_for_load_state("domcontentloaded")
        
        # Login
        print("🔑 Logging in...")
        page.fill("input[name*='User']", USERNAME)
        page.fill("input[name*='Pass']", PASSWORD)
        page.click("input[name*='Login']")
        
        # Navigate to Marketplace
        print("⏳ Waiting for Dashboard...")
        page.wait_for_url("**/Home.aspx**", timeout=30000)
        
        with context.expect_page() as new_page_info:
            print("👉 Clicking Marketplace...")
            page.click("a:has-text('Market')")
            market_page = new_page_info.value
            market_page.wait_for_load_state("domcontentloaded")
            
        print("✅ Inside Marketplace.")
        time.sleep(5)
        
        # --- THE SEARCH FOR THE FOOTER ---
        print("\n🔍 SCANNING FOOTER ELEMENTS...")
        
        # 1. Look for Dropdowns (Select 200)
        # We look for 'combobox', 'select', or specific text labels
        print("   Checking for 'Page Size' controls:")
        
        # Try generic text search
        size_dropdown = market_page.get_by_text("10", exact=True).or_(market_page.get_by_text("items per page"))
        if size_dropdown.count() > 0:
            print("   FOUND TEXT '10' or 'items per page'. Listing matches:")
            for i in range(size_dropdown.count()):
                print(f"      Match {i}: {size_dropdown.nth(i).evaluate('el => el.outerHTML')}")
        
        # Look for standard Select elements
        selects = market_page.query_selector_all("select")
        for i, s in enumerate(selects):
            print(f"   Select Box #{i}: ID='{s.get_attribute('id')}' Class='{s.get_attribute('class')}'")

        # 2. Look for Pagination (Next Arrow)
        print("\n   Checking for 'Next Page' arrow:")
        # Look for typical pagination classes
        paginations = market_page.query_selector_all("ul.pagination li, button[class*='page'], a[class*='next']")
        for i, p in enumerate(paginations):
            text = p.inner_text().strip()
            html = p.evaluate("el => el.outerHTML")
            print(f"      Pager {i} (Text='{text}'): {html[:100]}...")

        print("\n📸 Taking 'footer_debug.png'...")
        market_page.screenshot(path="footer_debug.png")
        
        print("😴 Closing...")
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    run()
