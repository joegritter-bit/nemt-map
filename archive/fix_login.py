from playwright.sync_api import sync_playwright
import time

def cut_new_keys():
    print("🚀 Launching Chrome in SAFE MODE (Fixing White Screen)...")

    with sync_playwright() as p:
        # 1. Launch Chrome directly with Graphics Disabled (Fixes blank screen)
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-gpu", "--disable-software-rasterizer"]
        )

        # 2. Create a fresh window
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        print("🌍 Navigating to MTM...")
        try:
            page.goto("https://mtm.mtmlink.net", timeout=60000)
        except:
            print("⚠️ Page load timed out (check the window!)")

        print("\n" + "="*50)
        print("👀  ACTION REQUIRED")
        print("1. The screen should be VISIBLE.")
        print("2. Log in manually.")
        print("3. WAIT until you see the list of trips.")
        print("="*50)

        # 3. Wait 3 minutes for you to login
        try:
            page.wait_for_url("**/pe/**", timeout=180000)
            print("\n🎉  Success! Dashboard reached.")

            # 4. Save the Keys (Cookies)
            context.storage_state(path="auth.json")
            print("💾  Keys saved to 'auth.json'.")

        except Exception:
            print("❌  Timed out. Did you reach the dashboard?")
            # Save anyway, sometimes it works even if we timed out
            context.storage_state(path="auth.json")

        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    cut_new_keys()
