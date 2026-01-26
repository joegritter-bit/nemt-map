from .base_scraper import BaseScraper
import os
import time
import random

class ModivcareScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.username = os.getenv("MODIVCARE_USER")
        self.password = os.getenv("MODIVCARE_PASS")
        self.login_url = "https://transportationco.logisticare.com/Login.aspx"
        self.market_page = None 

    def human_wiggle(self):
        try:
            for _ in range(random.randint(2, 4)):
                x, y = random.randint(100, 800), random.randint(100, 600)
                self.page.mouse.move(x, y, steps=random.randint(10, 20))
                time.sleep(random.uniform(0.05, 0.2))
        except: pass

    def login(self):
        print(f"   🌍 Navigating to Modivcare Login...")
        self.page.goto(self.login_url)
        self.page.wait_for_load_state("domcontentloaded")
        time.sleep(random.uniform(2, 3))

        try:
            print("   🔑 Entering Credentials...")
            self.page.type("input[name*='User']", self.username, delay=100)
            self.page.press("input[name*='User']", "Tab")
            self.page.type("input[name*='Pass']", self.password, delay=100)
            self.page.press("input[name*='Pass']", "Enter")
            
            print("   ⏳ Waiting for Dashboard...")
            self.page.wait_for_url("**/Home.aspx**", timeout=45000)
            print("   ✅ Modivcare Dashboard Reached.")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"   ❌ Modivcare Login Failed: {e}")
            return False

    def navigate_to_marketplace(self):
        print("   🔎 Looking for Marketplace link...")
        with self.context.expect_page() as new_page_info:
            clicked = False
            for link_text in ["Market", "Marketplace"]:
                try:
                    link = self.page.locator(f"a:has-text('{link_text}')").first
                    if link.is_visible():
                        print(f"      👉 Clicking '{link_text}'...")
                        link.click()
                        clicked = True
                        break
                except: continue

            if not clicked:
                print("   ❌ Could not find Marketplace link.")
                return False
            
            self.market_page = new_page_info.value
            self.market_page.wait_for_load_state("domcontentloaded")
            print("   ✅ Switched to Marketplace Tab.")
            time.sleep(5)
            return True

    def maximize_view(self):
        """Forces the table to show 200 items per page and VERIFIES it happened."""
        page = self.market_page
        print("   📏 Attempting to set view to 200 items...")
        
        try:
            # 1. Select the option
            page.select_option("select.form-select", value="200")
            
            # 2. FORCE the event (sometimes Select Option doesn't trigger the JS refresh)
            page.evaluate("document.querySelector('select.form-select').dispatchEvent(new Event('change'))")
            
            print("      ⏳ Waiting for table reload...")
            time.sleep(5)
            
            # 3. VERIFY
            rows = page.query_selector_all("tbody tr")
            print(f"      👀 Rows visible now: {len(rows)}")
            
            if len(rows) <= 10:
                print("      ⚠️ Warning: Row count didn't increase. Trying Fallback Click...")
                # Fallback: Click the select, then click the option manually (if it was a custom dropdown)
                page.click("select.form-select")
                time.sleep(0.5)
                page.keyboard.press("ArrowDown") # often moves to 25
                page.keyboard.press("ArrowDown") # 50
                page.keyboard.press("ArrowDown") # 100
                page.keyboard.press("ArrowDown") # 200
                page.keyboard.press("Enter")
                time.sleep(5)
                
        except Exception as e:
            print(f"      ⚠️ Error setting page size: {e}")

    def scrape_trips(self):
        self.maximize_view()
        
        all_trips = []
        page = self.market_page
        page_num = 1

        while True:
            print(f"   📖 Scraping Page {page_num}...")
            
            new_trips = self._parse_current_table()
            if new_trips:
                print(f"      Found {len(new_trips)} trips on this page.")
                all_trips.extend(new_trips)
            else:
                print("      (Page empty?)")

            # Check for Next Button
            try:
                # Look for the specific 'Next' arrow that is NOT disabled
                # The Modivcare 'Next' button usually has an aria-label or just text '>'
                next_btn = page.locator("li.page-item:not(.disabled) a:has-text('>')")
                
                if next_btn.count() > 0 and next_btn.first.is_visible():
                    print("      👉 Clicking Next Page...")
                    next_btn.first.click()
                    time.sleep(5) # Wait for reload
                    page_num += 1
                else:
                    print("      🛑 No more pages.")
                    break
            except:
                break

        return all_trips

    def _parse_current_table(self):
        trips = []
        page = self.market_page
        
        try:
            page.wait_for_selector("tbody tr", timeout=5000)
        except:
            return []

        rows = page.query_selector_all("tbody tr")
        for row in rows:
            try:
                cells = row.query_selector_all("td")
                if len(cells) < 15: continue

                date_text = cells[4].inner_text().strip()
                trip_id = cells[2].inner_text().strip()
                
                miles_text = cells[10].inner_text().replace('mi','').strip()
                miles = float(miles_text) if miles_text else 0.0
                
                pay_text = cells[7].inner_text().replace('$','').replace(',','').strip()
                pay = float(pay_text) if pay_text else 0.0
                
                pu_time = cells[12].inner_text().strip()
                pu_addr = f"{cells[14].inner_text()} {cells[15].inner_text()} {cells[16].inner_text()}"
                do_addr = f"{cells[17].inner_text()} {cells[18].inner_text()} {cells[19].inner_text()}"

                trips.append({
                    "trip_id": f"MOD-{trip_id}",
                    "date": date_text,
                    "pickup_time": pu_time,
                    "miles": miles,
                    "pickup_address": pu_addr.replace('\n', ' ').strip(),
                    "dropoff_address": do_addr.replace('\n', ' ').strip(),
                    "payout": pay,
                    "vehicle_type": "Modivcare",
                    "broker": "Modivcare"
                })
            except: continue
        return trips
