import subprocess
import shutil
import os
from config import get_logger

log = get_logger(__name__)

_HOME          = os.path.expanduser('~')
MAP_SOURCE     = os.path.join(_HOME, 'nemt-scraper', 'nemt_war_room.html')
MAP_REPO       = os.path.join(_HOME, 'nemt-map')
MAP_DEST       = os.path.join(MAP_REPO, 'index.html')
MAP_URL        = 'https://joegritter-bit.github.io/nemt-map/'
RIDERS_SOURCE  = os.path.join(MAP_REPO, 'regular_riders.json')

def publish_map():
    """Copy latest map to GitHub Pages repo and push."""
    try:
        if not os.path.exists(MAP_SOURCE):
            log.warning("nemt_war_room.html not found — skipping map publish")
            return None

        # Ensure we are on the 'master' branch (GitHub Pages branch).
        branch_result = subprocess.run(
            ['git', '-C', MAP_REPO, 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True)
        current_branch = branch_result.stdout.strip()
        if current_branch != 'master':
            log.warning(f"nemt-map repo is on branch '{current_branch}', switching to 'master'")
            subprocess.run(
                ['git', '-C', MAP_REPO, 'checkout', 'master'],
                capture_output=True, text=True)

        # Pull any remote commits (e.g. from worktree pushes) before adding
        # our own commit so the push is never rejected as non-fast-forward.
        pull_result = subprocess.run(
            ['git', '-C', MAP_REPO, 'pull', '--rebase', 'origin', 'master'],
            capture_output=True, text=True)
        if pull_result.returncode != 0:
            log.warning(f"Git pull --rebase failed: {pull_result.stderr.strip()}")

        shutil.copy2(MAP_SOURCE, MAP_DEST)

        subprocess.run(
            ['git', '-C', MAP_REPO, 'add', 'index.html'],
            capture_output=True, text=True)

        if os.path.exists(RIDERS_SOURCE):
            subprocess.run(
                ['git', '-C', MAP_REPO, 'add', 'regular_riders.json'],
                capture_output=True, text=True)

        driver_routes_path = os.path.join(MAP_REPO, 'driver_routes.json')
        if os.path.exists(driver_routes_path):
            subprocess.run(
                ['git', '-C', MAP_REPO, 'add', 'driver_routes.json'],
                capture_output=True, text=True)

        dashboard_path = os.path.join(_HOME, 'nemt-map', 'dashboard.html')
        if os.path.exists(dashboard_path):
            subprocess.run(
                ['git', '-C', MAP_REPO, 'add', 'dashboard.html'],
                capture_output=True, text=True)

        result = subprocess.run(
            ['git', '-C', MAP_REPO, 'commit', '-m', 'Update map and rider data'],
            capture_output=True, text=True)

        if 'nothing to commit' in result.stdout:
            log.info("Map unchanged — no push needed")
            return MAP_URL

        result = subprocess.run(
            ['git', '-C', MAP_REPO, 'push', 'origin', 'master'],
            capture_output=True, text=True)

        if result.returncode == 0:
            print(f"   🗺️  Map published: {MAP_URL}")
            return MAP_URL
        else:
            log.warning(f"Git push failed: {result.stderr}")
            return None

    except Exception as e:
        log.warning(f"Map publish failed: {e}")
        return None

if __name__ == "__main__":
    link = publish_map()
    print(f"Map URL: {link}")
