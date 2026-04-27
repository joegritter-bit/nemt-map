from config import get_logger, DB_PATH, ROUTES_FILE
from datetime import datetime
import os, sys, time

log = get_logger('pipeline')


def run_step(label, fn):
    print(f"\n{'='*50}\n▶ {label}\n{'='*50}")
    t0 = time.time()
    try:
        fn()
        elapsed = time.time() - t0
        print(f"✅ {label} completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - t0
        msg = f"❌ {label} FAILED: {e}"
        log.error(msg)
        print(msg)
        return False


def run_critical_step(label, fn):
    ok = run_step(label, fn)
    if not ok:
        print(f"\n🛑 Critical step failed — aborting pipeline.")
        sys.exit(1)
    return True


def run_assignments_scrape():
    """
    Run once per day to scrape MTM assignments and
    write driver_routes.json. Called from run_pipeline()
    only on the first run of the day.
    """
    import datetime, os

    flag_file = os.path.join(os.path.dirname(__file__), '.assignments_scraped_today')
    today = datetime.date.today().isoformat()

    if os.path.exists(flag_file):
        with open(flag_file) as f:
            scraped_date = f.read().strip()
        if scraped_date == today:
            print("[Assignments] Already scraped today, skipping")
            return

    print("[Assignments] Running daily assignments scrape...")

    try:
        from scrape_marketplace import MTMController
        scraper = MTMController()
        scraper.start_browser()

        if not scraper.perform_login():
            print("[Assignments] Login failed")
            scraper.close_browser()
            return

        driver_routes = scraper.scrape_assignments()

        if driver_routes:
            scraper.write_driver_routes(driver_routes)

            with open(flag_file, 'w') as f:
                f.write(today)

            print(f"[Assignments] Complete — {len(driver_routes)} drivers scraped")
        else:
            print("[Assignments] No driver data returned")

        scraper.close_browser()

    except Exception as e:
        print(f"[Assignments] Failed: {e}")


def run_pipeline():
    start_time = datetime.now().strftime('%H:%M:%S')
    pipeline_start = time.time()
    results = []

    # Daily assignments scrape (runs once per day)
    run_assignments_scrape()

    # ─── STAGE 1: MTM Scrape (critical) ───────────────────────────────────────
    from scrape_marketplace import MTMController
    def run_mtm():
        mtm = MTMController()
        mtm.run_scan()
    results.append(run_critical_step("MTM Marketplace Scrape", run_mtm))

    # ─── STAGE 2: Modivcare Scrape (non-critical) ─────────────────────────────
    from scrape_marketplace import run_modivcare
    results.append(run_step("Modivcare Marketplace Scrape", run_modivcare))

    # ─── STAGE 3: Route Analysis (critical) ───────────────────────────────────
    from find_complex_routes import find_complex_routes
    results.append(run_critical_step("Complex Route Analysis", find_complex_routes))

    # ─── STAGE 4: Springfield Dispatch (non-critical) ─────────────────────────
    from springfield_dispatch import get_springfield_dispatch
    def run_springfield():
        routes = get_springfield_dispatch()
        if routes:
            import pandas as pd
            pd.DataFrame(routes).to_csv('springfield_routes.csv', index=False)
            log.info(f"Springfield: {len(routes)} routes saved")
            print(f"   🏙️  Springfield: {len(routes)} routes dispatched")
        else:
            print("   🏙️  Springfield: No qualifying routes today")
    results.append(run_step("Springfield Dispatch", run_springfield))

    # ─── STAGE 4b: Regular Rider Export (non-critical) ────────────────────────
    from regular_riders import get_regular_rider_alerts
    def run_regular_riders():
        alerts = get_regular_rider_alerts()
        if alerts:
            print(f"   ⚡ Regular riders on marketplace: {len(alerts)}")
        else:
            print("   ⚡ No regular riders on marketplace")
    results.append(run_step("Regular Rider Export", run_regular_riders))

    # ─── STAGE 5: Driver Schedule Extensions (non-critical) ───────────────────
    from stitch_route import analyze_driver_schedule
    def run_stitch():
        res = analyze_driver_schedule()
        print(f"   🧵 Extensions found: {len(res)}")
    results.append(run_step("Driver Schedule Extensions", run_stitch))

    # ─── STAGE 6: Map Generation (non-critical) ───────────────────────────────
    from generate_map import generate_map
    results.append(run_step("Map Generation", generate_map))

    # ─── STAGE 6b: Sync Route Builder to Extension (non-critical) ────────────
    def sync_route_builder():
        import shutil
        _home = os.path.expanduser('~')
        files = ['route_builder.html', 'route_builder_main.js', 'route_builder_loader.js']
        for f in files:
            src = os.path.join(_home, 'nemt-scraper', f)
            dst = os.path.join(_home, 'nemt-extension', f)
            if os.path.exists(src):
                shutil.copy2(src, dst)
        print("   🔧 Route builder synced to extension")
    results.append(run_step("Sync Route Builder", sync_route_builder))

    # ─── STAGE 9: Email Report (non-critical) ─────────────────────────────────
    from analyze_patterns import analyze_and_report
    results.append(run_step("Email Report", analyze_and_report))

    # ─── STAGE 10: Team Dispatch Dashboard (non-critical) ─────────────────────
    from generate_dashboard import generate_dashboard
    def run_dashboard():
        generate_dashboard()
        print("   📊 Dashboard generated")
    results.append(run_step("Team Dispatch Dashboard", run_dashboard))

    # ─── STAGE 11: Publish Map & Dashboard to GitHub Pages (non-critical) ─────
    from map_updater import publish_map
    def run_publish():
        import shutil, os
        _home = os.path.expanduser('~')
        driver_routes_src = os.path.join(_home, 'nemt-scraper', 'driver_routes.json')
        driver_routes_dst = os.path.join(_home, 'nemt-map', 'driver_routes.json')
        if os.path.exists(driver_routes_src):
            shutil.copy(driver_routes_src, driver_routes_dst)
            print("   [Pipeline] Copied driver_routes.json to GitHub Pages")
        url = publish_map()
        if url:
            print(f"   🌐 Published to GitHub Pages: {url}")
        else:
            print("   ⚠️  GitHub Pages publish failed or nothing to push")
    results.append(run_step("Publish to GitHub Pages", run_publish))

    # ─── SUMMARY ──────────────────────────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start
    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"""
{'='*50}
PIPELINE COMPLETE
{'='*50}
Started:   {start_time}
Finished:  {datetime.now().strftime('%H:%M:%S')}
Duration:  {total_elapsed:.1f}s
Stages:    {passed}/{total} passed
Log file:  logs/nemt_pipeline.log
{'='*50}
""")


if __name__ == "__main__":
    run_pipeline()
