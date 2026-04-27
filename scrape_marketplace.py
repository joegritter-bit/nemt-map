import time
import random
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Import Custom Modules
from src.scrapers.broker_a import MTMScraper
from src.scrapers.broker_b import ModivcareScraper
from email_handler import EmailHandler
from database import save_batch

load_dotenv(override=True)

# --- 🔧 SETTINGS ---
DAYS_TO_SCAN = 8
HEADLESS_MODE = False  

class MTMController(MTMScraper):
    def __init__(self):
        super().__init__()
        self.consecutive_zeros = 0
        self.retry_queue = [] 

    # ✅ FORCE VISIBLE BROWSER
    def start_browser(self, headless=False, auth_file=None):
        print("   🚀 Launching Chrome (Force Visible Mode)...")
        self.p = sync_playwright().start()
        
        launch_args = ["--start-maximized", "--no-sandbox", "--disable-dev-shm-usage"]
        
        if auth_file and os.path.exists(auth_file):
            print(f"   🍪 Loading session from {auth_file}...")
            self.browser = self.p.chromium.launch_persistent_context(
                user_data_dir="user_data",
                headless=False, 
                args=launch_args,
                viewport={"width": 1280, "height": 800}
            )
            self.context = self.browser 
            self.page = self.browser.pages[0]
        else:
            self.browser = self.p.chromium.launch(
                headless=False, 
                args=launch_args
            )
            self.context = self.browser.new_context(viewport={"width": 1280, "height": 800})
            self.page = self.context.new_page()

    # ✅ HUMAN BEHAVIOR
    def human_wiggle(self):
        if self.page:
            try:
                for _ in range(random.randint(2, 4)):
                    x = random.randint(100, 700)
                    y = random.randint(100, 700)
                    self.page.mouse.move(x, y, steps=random.randint(10, 25))
                    time.sleep(random.uniform(0.1, 0.4))
            except: pass

    def perform_login(self):
        print("\n🔑 PERFORMING FRESH LOGIN (v10.85)...")
        print("   👀 LOOK AT THE BROWSER WINDOW NOW!")
        user = os.getenv("MTM_USERNAME")
        pwd = os.getenv("MTM_PASSWORD")
        
        try:
            self.page.goto("https://mtm.mtmlink.net/pe/login", timeout=60000)
            time.sleep(5) 

            # ✅ STRICT CHECK: Only return True if we see the DASHBOARD
            if self.page.locator("button:has-text('Apply Filter')").is_visible():
                print("   ✅ Already logged in (Dashboard found).")
                return True

            # Form Detection
            if not self.page.locator("#LoginEmail").is_visible():
                splash = self.page.locator("button:has-text('Sign In'), button.btn-primary").first
                if splash.is_visible() and splash.get_attribute("id") != "SignInButton":
                    print("   👉 Clicking Splash Button...")
                    self.human_wiggle()
                    splash.click()
                    time.sleep(3)

            print("   ✏️  Entering Credentials...")
            self.page.click("#LoginEmail")
            self.page.fill("#LoginEmail", "") 
            self.page.type("#LoginEmail", user, delay=random.randint(50, 100))
            self.page.keyboard.press("Tab") 
            time.sleep(random.uniform(0.5, 1.2))

            self.page.fill("#LoginPassword", "")
            self.page.type("#LoginPassword", pwd, delay=random.randint(50, 100))
            self.page.keyboard.press("Tab") 
            time.sleep(random.uniform(0.8, 1.5))

            submit_btn = self.page.locator("#SignInButton")
            for attempt in range(5):
                if submit_btn.is_disabled():
                    print(f"   ⚠️ Button disabled. Waking up form... ({attempt+1})")
                    self.page.click("#LoginPassword")
                    self.page.keyboard.type(" ")
                    self.page.keyboard.press("Backspace")
                    time.sleep(1)
                else:
                    break
            
            print("   👉 Clicking Sign In...")
            self.human_wiggle()
            submit_btn.click()
            time.sleep(5)

            # 🚨 STEP 1: CHECK FOR "REQUEST CODE" SCREEN
            if "RequestMFA" in self.page.url or self.page.locator("text=Request Authorization Code").is_visible():
                print("   🛡️  STEP 1: MFA Request Screen Detected!")
                try:
                    email_radio = self.page.locator("label:has-text('Email to:')")
                    if email_radio.count() > 0:
                        self.human_wiggle()
                        email_radio.click()
                except: pass

                send_btn = self.page.locator("button:has-text('Send Code')")
                if send_btn.is_visible():
                    print("      👉 Clicking 'Send Code'...")
                    self.human_wiggle()
                    send_btn.click()
                    self.page.wait_for_url("**/InputMFA**", timeout=15000)

            # 🚨 STEP 2: ENTER CODE SCREEN
            input_box = self.page.locator("input[name*='AuthorizationCode'], input[id*='Code'], input[type='text']")
            
            if input_box.count() > 0 and input_box.first.is_visible():
                print("   🔐 STEP 2: Enter Code Screen Detected!")
                print("      👉 Initializing Email Handler...")
                email_bot = EmailHandler()
                
                print("      ⌛ Waiting 20s for email to arrive...")
                time.sleep(20) 
                
                code = email_bot.get_latest_code()
                
                if code:
                    print(f"      ✅ Found Code: {code}")
                    input_box.first.fill("")
                    input_box.first.type(code, delay=random.randint(100, 200))
                    time.sleep(1)

                    try:
                        remember_box = self.page.locator("text=Remember this device")
                        if remember_box.count() > 0:
                            print("      ☑️  Clicking 'Remember this device'...")
                            self.human_wiggle()
                            remember_box.click()
                            time.sleep(1)
                    except: pass
                    
                    print("      👉 Clicking Submit...")
                    self.human_wiggle()
                    self.page.click("button:has-text('Submit')")
                else:
                    print("      ❌ Code not found in email.")

            # FINAL WAIT
            print("   ⌛ Waiting 5s for page load...")
            time.sleep(5)

            # ✅ THE FIX: BRUTE FORCE NAVIGATION
            if not self.page.locator("button:has-text('Apply Filter')").is_visible():
                print("   🔄 Dashboard not detected. Forcing navigation to Marketplace URL...")
                self.page.goto("https://mtm.mtmlink.net/pe/v1/marketplace?orgId=2853")
                time.sleep(5)

            # Verify Success
            try:
                self.page.wait_for_selector("button:has-text('Apply Filter')", timeout=20000)
                print("   ✅ Login Sequence Finished.")
                self.context.storage_state(path="auth.json")
                return True
            except:
                print("   ❌ Login Verification Failed (No Dashboard).")
                return False
            
        except Exception as e:
            print(f"   ❌ Login Crash: {e}")
            return False

    def check_service_area_toggle(self):
        print("   🔧 Checking 'Outside Service Area' Status...")
        try:
            time.sleep(3)
            red_indicator = self.page.locator("[fill='#c14a4c']").first
            if red_indicator.count() > 0:
                print("      🔴 Found RED Indicator (Switch is OFF). Clicking...")
                self.human_wiggle()
                red_indicator.click(force=True)
                print("      👉 Click sent. Waiting 5s...")
                time.sleep(5)
            else:
                print("      🟢 RED Indicator not found. Assuming Switch is ON.")
        except Exception as e: 
            print(f"      ⚠️ Toggle Error: {e}")

    def process_day(self, date_str):
        print(f"   [MTM] Scanning: {date_str}")
        self.change_date(date_str)
        self.human_wiggle() 
        self.page.click("button:has-text('Apply Filter')")
        
        try: self.page.wait_for_selector(".ant-spin-spinning", state='hidden', timeout=10000)
        except: pass

        try:
            self.page.wait_for_selector("tr.ant-table-row, div.ant-empty-image, .ant-empty-description", timeout=40000)
        except:
            print("      ⚠️ Timeout: Retrying filter click (Double Tap)...")
            self.page.click("button:has-text('Apply Filter')")
            time.sleep(3)
            try: self.page.wait_for_selector("tr.ant-table-row, div.ant-empty-image, .ant-empty-description", timeout=20000)
            except: 
                print("      ❌ Timeout: No data loaded.")
                return False

        trips = self.scrape_all_pages(date_str)
        if trips:
            print(f"      💰 Found {len(trips)} MTM trips.")
            try:
                save_batch(pd.DataFrame(trips))
            except Exception as e:
                if "UNIQUE" in str(e):
                    print(f"      🔄 Updated {len(trips)} existing trips.")
                else:
                    print(f"      ⚠️ Database Error: {e}")
            return True
        else:
            print("      ℹ️  No trips found (Marking for Retry).")
            return False

    def run_scan(self):
        print(f"\n🟢 STARTING MTM SCAN (Self-Healing Mode)...")
        
        # --- 🛡️ SELF-HEALING SESSION LOOP ---
        max_retries = 3
        attempt = 0
        session_ready = False

        while attempt < max_retries:
            attempt += 1
            print(f"\n🔄 SESSION INIT ATTEMPT {attempt}/{max_retries}...")
            
            auth_path = "auth.json" if os.path.exists("auth.json") else None
            self.start_browser(headless=HEADLESS_MODE, auth_file=auth_path) 
            time.sleep(3)

            try:
                target_url = "https://mtm.mtmlink.net/pe/v1/marketplace?orgId=2853"
                self.page.goto(target_url)
                time.sleep(3)

                login_form_visible = self.page.locator("#LoginEmail").is_visible()
                login_url = "login" in self.page.url.lower()
                
                if login_form_visible or login_url:
                    print("   ⚠️ Login Screen Detected. Proceeding to Login...")
                    if not self.perform_login():
                        raise Exception("Login Flow Failed")

                if "marketplace" not in self.page.url.lower():
                    print("   🔄 Force-navigating to Marketplace...")
                    self.page.goto(target_url)
                    time.sleep(5)

                try:
                    self.page.wait_for_selector("button:has-text('Apply Filter')", timeout=15000)
                    print("   ✅ Session Verified! 'Apply Filter' button found.")
                    session_ready = True
                    break 
                except:
                    raise Exception("Session Invalid - Dashboard Verification Failed")

            except Exception as e:
                print(f"   ❌ Session Error: {e}")
                print("   🗑️  HEALING: Deleting corrupt auth.json and restarting browser...")
                if os.path.exists("auth.json"): os.remove("auth.json")
                self.close_browser()
        
        if not session_ready:
            print("   ⛔ CRITICAL FAILURE: Could not establish session after retries.")
            return

        # --- 🚀 SCANNING PHASE ---
        try:
            self.check_service_area_toggle()

            try:
                self.page.click("button:has-text('Apply Filter')")
                time.sleep(3)
            except: pass

            start_date = datetime.now()
            
            for i in range(DAYS_TO_SCAN):
                target_date = start_date + timedelta(days=i)
                date_str = target_date.strftime("%m/%d/%Y")
                
                success = self.process_day(date_str)
                if not success:
                    print(f"      🔄 Adding {date_str} to Circle Back Queue.")
                    self.retry_queue.append(date_str)

                time.sleep(random.uniform(2.0, 4.0)) 

            if self.retry_queue:
                print(f"\n🔄 CIRCLING BACK: Retrying {len(self.retry_queue)} failed dates...")
                for date_str in self.retry_queue:
                    print(f"   [RETRY] Scanning: {date_str}")
                    self.process_day(date_str)
                    time.sleep(3)
            else:
                print("\n✨ Clean Sweep: No dates needed retrying.")

        except Exception as e:
            print(f"   ❌ Critical Error During Scan: {e}")
        
        self.close_browser()
        print("🔴 MTM SCAN COMPLETE.")

    def scrape_all_pages(self, date_str):
        all_trips = []
        while True:
            current = self.scrape_table(date_str)
            all_trips.extend(current)
            
            next_btn = self.page.locator('li.ant-pagination-next[aria-disabled="false"]').first
            if next_btn.count() > 0:
                try:
                    next_btn.click()
                    time.sleep(2) 
                except: break
            else: break
        return all_trips

    def change_date(self, date_str):
        try:
            sel = 'input[placeholder="Select date"], input.ant-calendar-picker-input'
            self.page.click(sel, click_count=3)
            self.page.keyboard.press("Backspace")
            self.page.type(sel, date_str, delay=random.randint(50, 150))
            self.page.keyboard.press("Enter")
            self.page.mouse.click(0,0) 
        except: pass

    def scrape_table(self, d):
        trips = []
        rows = self.page.query_selector_all("tr.ant-table-row")
        for row in rows:
            try:
                c = row.query_selector_all("td")
                if len(c) < 5: continue
                
                pickup_time = c[0].inner_text().strip()
                p_addr = c[2].inner_text().replace('\n', ', ').strip()
                d_addr = c[3].inner_text().replace('\n', ', ').strip()
                
                miles_txt = c[4].inner_text().lower().replace('mi','').strip()
                miles = float(miles_txt) if miles_txt else 0.0
                
                payout = 0.0
                for cell in c:
                    if '$' in cell.inner_text():
                        payout = float(cell.inner_text().replace('$','').replace(',','').strip())
                        break

                safe_date = d.replace('/', '')
                safe_addr = p_addr.replace(' ', '').replace(',', '')[:6]
                trip_id = f"{safe_date}-{pickup_time.replace(':', '')}-{safe_addr}"

                trips.append({
                    "trip_id": trip_id,
                    "date": d,
                    "pickup_time": pickup_time,
                    "pickup_address": p_addr,
                    "dropoff_address": d_addr,
                    "miles": miles,
                    "payout": payout,
                    "broker": "MTM",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except: continue
        return trips

    def scrape_assignments(self, date_str=None):
        """
        Scrape the MTM Assignments page for all drivers.
        Returns a dict of driver_name -> list of trip dicts.
        Member/patient names are used only to match
        Pick/Drop pairs and are never written to output.
        """
        import datetime

        if date_str is None:
            today = datetime.date.today()
            # Friday → next Monday (+3), Sat → Mon (+2), Sun → Mon (+1), else → tomorrow (+1)
            if today.weekday() == 4:    # Friday
                next_day = today + datetime.timedelta(days=3)
            elif today.weekday() == 5:  # Saturday
                next_day = today + datetime.timedelta(days=2)
            elif today.weekday() == 6:  # Sunday
                next_day = today + datetime.timedelta(days=1)
            else:
                next_day = today + datetime.timedelta(days=1)
            date_str = next_day.strftime('%m/%d/%Y')
            print(f"[Assignments] Using next business day: {date_str}")

        print(f"[Assignments] Scraping assignments for {date_str}")

        assignments_url = "https://mtm.mtmlink.net/pe/v1/assignments?orgId=2853"

        try:
            self.page.goto(assignments_url,
                           wait_until='networkidle',
                           timeout=30000)
            self.page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[Assignments] Navigation failed: {e}")
            return {}

        # Set date if needed
        try:
            date_input = self.page.query_selector(
                'input[class*="picker"], input[placeholder*="date"], '
                'input[placeholder*="Date"]')
            if date_input:
                date_input.click()
                self.page.wait_for_timeout(300)
                # Select all and replace
                date_input.evaluate('el => el.select()')
                date_input.type(date_str, delay=50)
                self.page.keyboard.press('Enter')
                self.page.wait_for_timeout(1000)
        except Exception as e:
            print(f"[Assignments] Date set failed: {e}")

        # Click Search to load driver list
        try:
            search_btn = self.page.query_selector('button:has-text("Search")')
            if search_btn:
                search_btn.click()
                self.page.wait_for_timeout(2000)
                print("[Assignments] DEBUG: After search, URL:", self.page.url)
                body_text = self.page.evaluate('document.body.innerText')
                print("[Assignments] DEBUG: Page text after search:")
                print(body_text[:1000])
        except Exception as e:
            print(f"[Assignments] Search click failed: {e}")
            return {}

        driver_routes = {}

        while True:
            # Try multiple selector strategies for driver names
            driver_names = []

            # Strategy 1: Look for elements near "Trip" count text
            all_elements = self.page.query_selector_all(
                'h3, h4, [class*="name"], [class*="Name"], '
                '[class*="driver"], [class*="Driver"], '
                '[class*="title"], [class*="Title"]')

            seen_names = set()
            for el in all_elements:
                try:
                    text = el.inner_text().strip()
                    if (text and
                            len(text) > 3 and
                            len(text) < 50 and
                            text not in seen_names and
                            text not in ('Assignment Management', 'Search',
                                         'All Drivers', 'Map', 'Satellite') and
                            not text.startswith('0') and
                            not text.isdigit()):
                        parent = el.evaluate_handle(
                            'el => el.closest("div, li, tr, section")')
                        parent_text = parent.evaluate(
                            'el => el ? el.innerText : ""')
                        if 'Trip' in parent_text or 'trip' in parent_text:
                            driver_names.append((text, el))
                            seen_names.add(text)
                except:
                    continue

            # Strategy 2: If nothing found, dump page text for debugging
            if not driver_names:
                print("[Assignments] DEBUG: Page URL:", self.page.url)
                print("[Assignments] DEBUG: Page title:", self.page.title())
                body_text = self.page.evaluate('document.body.innerText')
                print("[Assignments] DEBUG page text (first 2000):")
                print(body_text[:2000])
                print("[Assignments] No driver cards found")
                break

            print(f"[Assignments] Found {len(driver_names)} drivers")

            for driver_name, card_el in driver_names:
                try:
                    print(f"[Assignments] Scraping {driver_name}...")
                    card_el.click()
                    self.page.wait_for_timeout(1500)

                    trips = self._parse_assignment_trips()

                    if trips:
                        driver_routes[driver_name] = trips
                        print(f"[Assignments] {driver_name}: {len(trips)} trips")

                    search_btn = self.page.query_selector('button:has-text("Search")')
                    if search_btn:
                        search_btn.click()
                        self.page.wait_for_timeout(1500)

                except Exception as e:
                    print(f"[Assignments] Error on {driver_name}: {e}")
                    continue

            next_btn = self.page.query_selector(
                'button[aria-label="right"], '
                '.ant-pagination-next:not(.ant-pagination-disabled)')
            if next_btn:
                next_btn.click()
                self.page.wait_for_timeout(1500)
            else:
                break

        return driver_routes

    def _parse_assignment_trips(self):
        """
        Parse Pick/Drop pairs from the assignment detail table.
        Matches pairs by member name, then discards names (HIPAA).
        Returns list of {pickup, dropoff, time, miles} dicts.
        """
        import re
        from collections import defaultdict

        trips = []

        try:
            self.page.wait_for_selector('table, [class*="table"]', timeout=5000)
            self.page.wait_for_timeout(500)

            rows = self.page.query_selector_all('tr.ant-table-row, tbody tr')

            stops = []
            for row in rows:
                cells = row.query_selector_all('td')
                if len(cells) < 4:
                    continue

                stop_type    = cells[1].inner_text().strip() if len(cells) > 1 else ''
                member_info  = cells[2].inner_text().strip() if len(cells) > 2 else ''
                stop_address = cells[4].inner_text().replace('\n', ', ').strip() if len(cells) > 4 else ''
                proj_time    = cells[5].inner_text().strip() if len(cells) > 5 else ''

                if 'depot' in stop_type.lower():
                    continue

                stop_type_lower = stop_type.lower()
                if 'pick' not in stop_type_lower and 'drop' not in stop_type_lower:
                    continue

                stops.append({
                    'type':    'pick' if 'pick' in stop_type_lower else 'drop',
                    'member':  member_info,  # temp — for matching only
                    'address': stop_address,
                    'time':    proj_time
                })

            # Match Pick/Drop pairs by member name, then discard names
            by_member = defaultdict(list)
            for stop in stops:
                by_member[stop['member']].append(stop)

            for member, member_stops in by_member.items():
                picks = [s for s in member_stops if s['type'] == 'pick']
                drops = [s for s in member_stops if s['type'] == 'drop']

                for i in range(min(len(picks), len(drops))):
                    trips.append({
                        'pickup':  picks[i]['address'],
                        'dropoff': drops[i]['address'],
                        'time':    picks[i]['time'] or drops[i]['time'],
                        'miles':   None  # calculated by route builder
                        # member name intentionally excluded
                    })

            def parse_time(t):
                if not t or t == 'N/A':
                    return 9999
                m = re.match(r'(\d+):(\d+)\s*(AM|PM)', t, re.I)
                if not m:
                    return 9999
                h, mn = int(m.group(1)), int(m.group(2))
                if m.group(3).upper() == 'PM' and h != 12:
                    h += 12
                if m.group(3).upper() == 'AM' and h == 12:
                    h = 0
                return h * 60 + mn

            trips.sort(key=lambda t: parse_time(t['time']))

        except Exception as e:
            print(f"[Assignments] Parse error: {e}")

        return trips

    def write_driver_routes(self, driver_routes, date_str=None):
        """
        Write driver_routes.json for the route builder.
        No patient/member names in output (HIPAA compliance).
        """
        import datetime, json, os

        if date_str is None:
            date_str = datetime.date.today().strftime('%m/%d/%Y')

        output = {
            'date':         date_str,
            'generated_at': datetime.datetime.now().strftime('%I:%M %p'),
            'drivers':      driver_routes
        }

        output_path = os.path.join(os.path.dirname(__file__), 'driver_routes.json')

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"[Assignments] Wrote driver_routes.json — {len(driver_routes)} drivers")
        return output_path


# --- MODIVCARE CONTROLLER ---
def run_modivcare():
    print("\n🔵 STARTING MODIVCARE SCAN...")
    try:
        bot = ModivcareScraper()
        bot.start_browser() 
        time.sleep(3)
        if bot.login():
            if bot.navigate_to_marketplace():
                trips = bot.scrape_trips()
                if trips:
                    print(f"   💰 Found {len(trips)} Modivcare trips!")
                    save_batch(pd.DataFrame(trips))
        bot.close_browser()
    except Exception as e:
        print(f"   ⚠️ Modivcare Warning: {e}")
    print("🔴 MODIVCARE SCAN COMPLETE.")

if __name__ == "__main__":
    print("Run run_pipeline.py to execute the full pipeline.")