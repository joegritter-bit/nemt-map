from src.scrapers.broker_a import MTMScraper
from src.scrapers.broker_b import ModivcareScraper
from analyze_patterns import analyze_and_report
from generate_map import generate_map
from email_handler import EmailHandler
from datetime import datetime, timedelta
import time
import random
import os
import pandas as pd
from dotenv import load_dotenv
from database import save_batch

load_dotenv(override=True)

DAYS_TO_SCAN = 8

class MTMController(MTMScraper):
    def human_wiggle(self):
        """ Adds random mouse movements to look human. """
        if self.page:
            try:
                # Move mouse in a random arc/path
                for _ in range(random.randint(2, 4)):
                    x = random.randint(100, 700)
                    y = random.randint(100, 700)
                    self.page.mouse.move(x, y, steps=random.randint(5, 15))
                    time.sleep(random.uniform(0.1, 0.3))
            except: pass

    def perform_auto_login(self):
        print("\n🚨 MTM SESSION EXPIRED. AUTO-LOGIN...")
        user = os.getenv("MTM_USERNAME")
        pwd = os.getenv("MTM_PASSWORD")
        
        try:
            print("   🌍 Navigating to Login...")
            # UPDATE 1: Increased Timeout to 60s
            self.page.goto("https://mtm.mtmlink.net/pe/login", timeout=60000)
            
            # UPDATE 2: Print Title to check for Cloudflare blocks
            try:
                print(f"      👀 Page Title: {self.page.title()}")
            except: pass

            # UPDATE 3: Wait longer for the username field
            self.page.wait_for_selector("input[id='Username'], input[name='Username']", timeout=60000)
            
            print("   🔑 Typing Credentials...")
            self.human_wiggle() # Wiggle before typing
            self.page.type("input[id='Username'], input[name='Username']", user, delay=random.randint(50, 150))
            self.page.type("input[id='Password'], input[name='Password']", pwd, delay=random.randint(50, 150))
            
            self.page.click("button[type='submit'], button:has-text('Login')")
            
            # MFA Handler
            try:
                # Wait for MFA field to appear
                self.page.wait_for_selector("input[id='code']", timeout=10000)
                print("   🔒 MFA Detected! Checking Gmail...")
                
                email_bot = EmailHandler()
                time.sleep(15) # Give email time to arrive
                
                code = email_bot.get_latest_code()
                if code:
                    print(f"      ✅ Found Code: {code}")
                    self.page.fill("input[id='code']", code)
                    self.page.click("button[type='submit']")
                else:
                    print("      ❌ No MFA code found in email.")
            except: 
                # If no MFA field appears, assume we logged in directly
                pass

            self.page.wait_for_url("**/pe/**", timeout=60000)
            print("   ✅ Login Success!")
            self.context.storage_state(path="auth.json")
            return True
            
        except Exception as e:
            print(f"   ❌ Login Failed: {e}")
            self.page.screenshot(path="mtm_login_fail.png")
            return False

    def run_scan(self):
        print("\n🟢 STARTING MTM BROKER SCAN (Invisible Mode)...")
        # FORCE HEADLESS = TRUE for background automation
        self.start_browser(headless=True, auth_file="auth.json") 
        
        try:
            self.page.goto("https://mtm.mtmlink.net/pe/v1/marketplace?orgId=2853")
            
            # Check if we need to login
            login_needed = False
            try:
                self.page.wait_for_selector('div[class*="toggleServiceArea"]', timeout=8000)
            except:
                login_needed = True

            if login_needed:
                if not self.perform_auto_login():
                    print("   ⛔ MTM Login failed. Skipping MTM.")
                    self.close_browser()
                    return
                # If login succeeded, go back to marketplace
                self.page.goto("https://mtm.mtmlink.net/pe/v1/marketplace?orgId=2853")

            # Click 'Toggle Service Area'
            try:
                self.human_wiggle() # Wiggle before toggle
                self.page.click('div[class*="toggleServiceArea"]')
                time.sleep(3)
            except: pass

            start_date = datetime.now()
            failed_dates = []

            # PHASE 1: Main Sweep
            for i in range(DAYS_TO_SCAN):
                target_date = start_date + timedelta(days=i)
                date_str = target_date.strftime("%m/%d/%Y")
                print(f"   [MTM] Scanning: {date_str}")
                
                if not self.process_date(date_str):
                    print(f"      ⚠️ Load failed. Adding to 'Circle Back' list.")
                    failed_dates.append(date_str)
                
                # Random pause between dates to look human
                time.sleep(random.uniform(1.5, 3.0))

            # PHASE 2: Circle Back
            if failed_dates:
                print(f"\n🔄 Circling back to retry {len(failed_dates)} dates...")
                time.sleep(random.randint(3, 6))
                for date_str in failed_dates:
                    print(f"   [MTM] Retrying: {date_str}")
                    if self.process_date(date_str):
                        print("      ✅ Recovered!")
                    else:
                        print("      ❌ Still stuck. Skipping.")

        except Exception as e:
            print(f"   ❌ MTM Critical Error: {e}")
            self.page.screenshot(path="mtm_crash.png")
        
        self.close_browser()
        print("🔴 MTM SCAN COMPLETE.")

    def process_date(self, date_str):
        self.change_date(date_str)
        self.human_wiggle() # Wiggle before clicking apply
        self.click_apply_filter()
        
        if self.wait_for_results(15):
            trips = self.scrape_all_pages(date_str)
            if trips:
                print(f"      💰 Found {len(trips)} MTM trips (Total).")
                save_batch(pd.DataFrame(trips))
            return True
        else: 
            return False

    def scrape_all_pages(self, date_str):
        all_trips = []
        page_num = 1
        
        while True:
            print(f"      📖 Scraping MTM Page {page_num}...")
            
            current_page_trips = self.scrape_table(date_str)
            all_trips.extend(current_page_trips)
            
            next_btn_selector = 'li.ant-pagination-next[aria-disabled="false"]'
            
            if self.page.query_selector(next_btn_selector):
                try:
                    self.human_wiggle() # Wiggle before clicking next
                    self.page.click(next_btn_selector)
                    time.sleep(random.uniform(3.0, 5.0)) 
                    page_num += 1
                except Exception as e:
                    print(f"      ⚠️ Pagination Click Failed: {e}")
                    break
            else:
                break
                
        return all_trips

    def change_date(self, date_str):
        try:
            sel = 'input[placeholder="Select date"]'
            self.page.click(sel, click_count=3)
            self.page.keyboard.press("Backspace")
            self.page.type(sel, date_str, delay=random.randint(50, 100))
            self.page.keyboard.press("Enter")
            self.page.mouse.click(0,0)
        except: pass

    def click_apply_filter(self):
        try: 
            self.page.click("button:has-text('Apply Filter')")
            time.sleep(random.uniform(1.0, 2.0))
        except: pass

    def wait_for_results(self, t):
        try:
            self.page.wait_for_selector("tr.ant-table-row, .ant-empty-image", timeout=t*1000)
            time.sleep(1)
            return True
        except: return False

    def scrape_table(self, d):
        trips = []
        for row in self.page.query_selector_all("tr.ant-table-row"):
            try:
                c = row.query_selector_all("td")
                if len(c)<5: continue
                
                pickup = c[0].inner_text()
                p_addr = c[2].inner_text().replace('\n', ', ')
                trip_id = f"{d}-{pickup}-{p_addr[:5]}"
                
                trips.append({
                    "trip_id": trip_id,
                    "date": d,
                    "pickup_time": pickup,
                    "miles": float(c[4].inner_text().lower().replace('mi','').strip() or 0),
                    "pickup_address": p_addr,
                    "dropoff_address": c[3].inner_text().replace('\n', ', '),
                    "broker": "MTM"
                })
            except: continue
        return trips

# --- MODIVCARE CONTROLLER ---
def run_modivcare():
    print("\n🔵 STARTING MODIVCARE SCAN (Invisible Mode)...")
    bot = ModivcareScraper()
    bot.start_browser() 
    time.sleep(random.uniform(2, 5))
    if bot.login():
        if bot.navigate_to_marketplace():
            trips = bot.scrape_trips()
            if trips:
                print(f"   💰 Found {len(trips)} Modivcare trips!")
                save_batch(pd.DataFrame(trips))
    bot.close_browser()
    print("🔴 MODIVCARE SCAN COMPLETE.")

if __name__ == "__main__":
    mtm = MTMController()
    mtm.run_scan()
    print("😴 Resting...")
    time.sleep(random.randint(10, 20))
    try: run_modivcare()
    except Exception as e: print(f"❌ Modivcare Error: {e}")

    # UPDATE MAP FIRST
    try: generate_map()
    except: pass

    # THEN SEND EMAIL
    analyze_and_report()