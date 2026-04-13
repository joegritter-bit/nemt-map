from playwright.sync_api import sync_playwright

print("🚀 Attempting to launch Chromium...")
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        print("✅ SUCCESS! Browser launched.")
        print(f"📍 Browser Version: {browser.version}")
        browser.close()
except Exception as e:
    print(f"❌ REAL ERROR: {e}")