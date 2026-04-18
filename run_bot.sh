#!/bin/bash

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# 1. PASTE YOUR HEALTHCHECKS URL HERE:
PING_URL="https://hc-ping.com/7adc3d36-274a-4002-838d-4b26174b3a0d"

# 2. PATHS (Do not change unless you move folders)
BACKUP_DIR="$HOME/Library/CloudStorage/GoogleDrive-owner@effinghamtransport.com/My Drive/NEMT_Bot_Backup"
SOURCE_DIR="$HOME/nemt-scraper"
ENV_PATH="$HOME/nemt-scraper/nemt_env"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")

# ==========================================
# 🔒 PHASE 0: LOCKFILE (Prevent stacking)
# ==========================================
LOCKFILE="$SOURCE_DIR/bot.lock"

if [ -f "$LOCKFILE" ]; then
    LOCKED_PID=$(cat "$LOCKFILE")
    if kill -0 "$LOCKED_PID" 2>/dev/null; then
        echo "⏭️  Previous run (PID $LOCKED_PID) still active — skipping this cycle."
        exit 0
    else
        echo "🧹 Stale lockfile found (PID $LOCKED_PID gone) — clearing and continuing."
        rm -f "$LOCKFILE"
    fi
fi

echo $$ > "$LOCKFILE"
trap "rm -f '$LOCKFILE'" EXIT

# ==========================================
# 🎭 PHASE 1: HUMAN JITTER (Anti-Detection)
# ==========================================
# Sleep for a random time between 0 and 300 seconds (5 mins)
# This prevents the bot from hitting MTM exactly at 8:00:00 every time.
SLEEP_TIME=$((RANDOM % 300))
echo "😴 Yawning for ${SLEEP_TIME} seconds to act human..."
sleep $SLEEP_TIME

# ==========================================
# 🚀 PHASE 2: LAUNCH SEQUENCE
# ==========================================
echo "🤖 Auto-Bot started at $(date)"
cd $SOURCE_DIR

# Activate Python Environment
if [ -f "$ENV_PATH/bin/activate" ]; then
    source "$ENV_PATH/bin/activate"
else
    echo "❌ CRITICAL ERROR: Environment not found at $ENV_PATH"
    exit 1
fi

# ==========================================
# 🌐 PHASE 2b: ROUTE BUILDER SERVER
# ==========================================
if ! pgrep -f "route_server.py" > /dev/null; then
    echo "🌐 Starting Route Builder server..."
    nohup python "$SOURCE_DIR/route_server.py" \
        > "$SOURCE_DIR/logs/route_server.log" 2>&1 &
    echo "✅ Route Builder server started (PID $!)"
else
    echo "✅ Route Builder server already running"
fi

# ==========================================
# 🕸️ PHASE 3: RUN THE SCRAPER & ANALYSIS
# ==========================================
# We use 'main.py' as the primary script. 
# It returns a success code (0) if it works, or error (1) if it crashes.

if python3 run_pipeline.py; then
    echo "✅ Pipeline completed successfully."

    # Ping the Dead Man's Switch (Watchdog)
    # This tells Healthchecks.io "I'm alive, reset the timer."
    # We allow 10 seconds for the ping to connect (-m 10)
    curl -fsS -m 10 --retry 5 -o /dev/null "$PING_URL"
    echo "📡 Ping sent to Healthchecks.io - Timer Reset."

else
    echo "❌ Scraper Crashed! No ping sent."
    # We do NOT ping here. 
    # Silence = Failure = You get an email alert from Healthchecks.io.
    exit 1
fi

# ==========================================
# 💾 PHASE 4: THE ESCAPE POD (Cloud Backup)
# ==========================================
# Only runs if the scrape didn't crash early
echo "💿 Starting Cloud Backup..."

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# 1. Backup the Database (The most important file)
cp $SOURCE_DIR/data/nemt_data.db "$BACKUP_DIR/nemt_data_LATEST.db"

# 2. Backup the Code & Config (Excluding heavy/useless folders)
zip -r "$BACKUP_DIR/code_backup_$TIMESTAMP.zip" $SOURCE_DIR -x "*nemt_env*" "*__pycache__*" "*.git*"

echo "✅ Backup sent to Google Drive!"
echo "========================================"
