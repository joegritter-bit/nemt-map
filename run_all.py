import subprocess
import sys
import time

def run_script(script_name):
    print(f"\n{'='*50}")
    print(f"🚀 EXECUTING: {script_name}")
    print(f"{'='*50}")
    
    try:
        # Runs the script and waits for it to finish
        result = subprocess.run([sys.executable, script_name], check=True)
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully.")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR in {script_name}: Script exited with errors.")
        return False
    except Exception as e:
        print(f"❌ CRITICAL FAILURE: {e}")
        return False

def main():
    start_time = time.time()
    
    # 1. Update the local database with latest market trips
    if not run_script("scrape_marketplace.py"):
        print("🛑 Pipeline stopped: Scraper failed.")
        return

    # 2. Run Strategic Routing (Effingham-only logic + County IDs)
    if not run_script("find_new_routes.py"):
        print("🛑 Pipeline stopped: Route Analysis failed.")
        return

    # 3. Generate the Interactive Map (v10.11 Price-Aware / Iron Dome)
    if not run_script("generate_map.py"):
        print("🛑 Pipeline stopped: Map Generation failed.")
        return

    # 4. Generate & Send the Comprehensive Strategic Report
    if not run_script("analyze_patterns.py"):
        print("🛑 Pipeline stopped: Report/Email failed.")
        return

    elapsed = round((time.time() - start_time) / 60, 2)
    print(f"\n{'='*50}")
    print(f"🏁 PIPELINE COMPLETE in {elapsed} minutes.")
    print("📧 Check your email for the Strategic Update.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()