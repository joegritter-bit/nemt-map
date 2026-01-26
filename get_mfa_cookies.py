from playwright.sync_api import sync_playwright
import time

def manual_login_direct():
    print("🚀 Launching Chrome Directly (Bypassing Bot Code)...")

    with sync_playwright() as p:
        # We launch Chrome directly with the fix for the White Screen
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-gpu", "--disable-software-rasterizer"]
        )

        # Create a standard browser window
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        print("🌍 Navigating to MTM...")
        try:
            page.goto("https://mtm.mtmlink.net", timeout=60000)
        except:
            print("⚠️ Page load timed out, but check the window.")

        print("\n" + "="*50)
        print("👀  ACTION REQUIRED")
        print("1. The screen should be VISIBLE now.")
        print("2. Log in manually.")
        print("3. Wait for the Dashboard.")
        print("="*50)

        try:
            # Wait 3 minutes for you to finish logging in
            page.wait_for_url("**/pe/**", timeout=180000)
            print("\n🎉  Success! Dashboard reached.")

            # Save the cookies to the file the main bot expects
            context.storage_state(path="auth.json")
            print("💾  Session saved to 'auth.json'.")
        except:
            print("❌  Timed out waiting for dashboard.")
            # Save anyway just in case the URL was weird
            context.storage_state(path="auth.json")

        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    manual_login_direct()
