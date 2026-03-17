import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from email_handler import send_email
from stitch_route import analyze_driver_schedule
import warnings
import os
import re

warnings.filterwarnings('ignore')

# CONFIG
DB_PATH = 'data/nemt_data.db'
CLINICS_FILE = 'clinics.txt'
ROUTES_FILE = 'potential_routes.csv'
MAP_FILE_PATH = 'nemt_war_room.html'
PULSE_FILE = 'data/market_pulse.csv'

STRICT_MAX_HOURS = 11.0
MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT = 1.50, 5.0
STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE = 20.00, 20.00

# 💰 MTM CONTRACT RATES
COUNTY_BASE_RATES = {
    "Sangamon County": 65.00, "Vermilion County": 65.00,
    "Marion County": 50.00, "Jefferson County": 50.00,
    "Coles County": 40.00, "Fayette County": 40.00, "Clay County": 40.00, "Edgar County": 40.00, "Clark County": 40.00,
    "Christian County": 35.00, "Macon County": 35.00, "Piatt County": 35.00, "Champaign County": 35.00
}

CITY_COUNTY_MAP = {
    "springfield": "Sangamon County", "chatham": "Sangamon County",
    "mattoon": "Coles County", "charleston": "Coles County", "oakland": "Coles County",
    "decatur": "Macon County", "champaign": "Champaign County",
    "urbana": "Champaign County", "danville": "Vermilion County", "indianola": "Vermilion County",
    "effingham": "Effingham County", "vandalia": "Fayette County",
    "centralia": "Marion County", "salem": "Marion County",
    "mt vernon": "Jefferson County", "mt. vernon": "Jefferson County",
    "taylorville": "Christian County", "monticello": "Piatt County",
    "louisville": "Clay County", "flora": "Clay County",
    "paris": "Edgar County", "casey": "Clark County", "marshall": "Clark County"
}

def get_db_connection():
    if os.path.exists(DB_PATH): return sqlite3.connect(DB_PATH)
    return sqlite3.connect('trips.db')

def load_priority_keywords():
    default = ["DaVita", "Fresenius", "Dialysis", "Cancer", "Radiation"]
    if not os.path.exists(CLINICS_FILE): return default
    try:
        with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except: return default

def smart_clean_addr(addr):
    if not addr: return "Unknown"
    return addr.split(',')[0].strip() if ',' in addr else addr[:30]

def get_robust_price(row, cached_county="Unknown"):
    if row.get('broker') == 'Modivcare':
        try: return float(row.get('payout', 0))
        except: return 0.0
    if cached_county == "Unknown" or not cached_county:
        addr = str(row.get('pickup_address', '')).lower()
        for city, c_name in CITY_COUNTY_MAP.items():
            if city in addr: cached_county = c_name; break
    try:
        pt = pd.to_datetime(row['pickup_time']).time()
        is_after = pt.hour < 6 or pt.hour >= 18
        base = AFTER_HOURS_BASE_RATE if is_after else COUNTY_BASE_RATES.get(cached_county, STANDARD_BASE_RATE)
        miles = float(row.get('miles', 0))
        return round((base + (max(0, miles - MILEAGE_BAND_LIMIT) * MTM_MILEAGE_RATE)) * 2, 2)
    except: return 0.0

def track_market_pulse(active_count):
    now = datetime.now()
    new_row = {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "count": active_count, "hour": now.hour}
    if not os.path.exists("data"): os.makedirs("data")
    try: pd.DataFrame([new_row]).to_csv(PULSE_FILE, mode='a', header=not os.path.exists(PULSE_FILE), index=False)
    except: pass

def analyze_market_pulse():
    if not os.path.exists(PULSE_FILE): return "Insufficient Data"
    try:
        df = pd.read_csv(PULSE_FILE)
        df['dt'] = pd.to_datetime(df['timestamp'], format='mixed')
        cutoff = datetime.now() - timedelta(days=3)
        recent = df[df['dt'] >= cutoff]
        if recent.empty: return "Insufficient Data"
        hourly_avg = recent.groupby('hour')['count'].mean()
        peak_hour = hourly_avg.idxmax()
        if len(df) >= 2:
            last, prev = df.iloc[-1]['count'], df.iloc[-2]['count']
            trend = "📈 Rising" if last > prev else "📉 Falling" if last < prev else "➡️ Stable"
        else: trend = "Analyzing..."
        return f"{trend} (Peak Activity: {peak_hour}:00)"
    except: return "Analyzing..."

def analyze_and_report():
    print("📊 Generating COMPREHENSIVE Strategic Report v12.3...")
    
    # 🛠 SELF-HEALING: Clear stuck browser locks
    os.system("rm -rf /home/joegritter/nemt-scraper/user_data/Default/SingletonLock 2>/dev/null")
    
    priority_keywords = load_priority_keywords()
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        cache_df = pd.read_sql_query("SELECT address, county FROM geo_cache", conn)
        county_map = dict(zip(cache_df['address'], cache_df['county']))
    except Exception as e: print(f"❌ Database Error: {e}"); return

    if df.empty: return

    # --- 🟢 SNAPSHOT INTEGRITY: Define ACTIVE trips ---
    time_col = 'last_seen' if 'last_seen' in df.columns else 'timestamp'
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    latest_scan_time = df[time_col].max()
    
    # Snapshot Pulse (Last 120 Mins to match stitch_route v11.8)
    df_active = df[df[time_col] >= (latest_scan_time - timedelta(minutes=120))].copy()
    pulse_count = len(df_active)
    track_market_pulse(pulse_count)

    for d in [df_active, df]:
        d['broker'] = d['broker'].fillna('MTM')
        d['simple_pickup'] = d['pickup_address'].apply(smart_clean_addr)
        d['simple_dropoff'] = d['dropoff_address'].apply(smart_clean_addr)

    # 1. TOP STRATEGIC ROUTES
    top_routes = []
    if os.path.exists(ROUTES_FILE):
        try:
            r_df = pd.read_csv(ROUTES_FILE)
            r_df = r_df[(r_df['Shift Length (Hrs)'] <= STRICT_MAX_HOURS) & (r_df['Revenue/Hour'] >= 39.0)]
            r_df['Date_Obj'] = pd.to_datetime(r_df['Date'])
            top_routes = r_df.sort_values(by=['Date_Obj', 'Revenue/Hour'], ascending=[True, False]).to_dict('records')
        except: pass

    brandy_matches = analyze_driver_schedule()
    market_status = analyze_market_pulse()
    refresh_time = latest_scan_time.strftime('%H:%M')
    subject = f"NEMT Command | {len(top_routes)} Shifts | {market_status}"

    body = f"""<html><body style="font-family: Arial, sans-serif; color: #333;">
    <div style="background-color: #2c3e50; color: white; padding: 15px;">
        <h2 style="margin:0;">🚀 NEMT Commander v12.3</h2>
        <p style="margin:5px 0 0 0;">Market: {market_status} | {pulse_count} active trips | Refreshed: {refresh_time}</p>
    </div>"""

    # --- 💰 SECTION: MTM CONTRACTED RATES ---
    body += '<h3 style="color: #2980b9; border-bottom: 2px solid #2980b9; margin-top: 25px;">💰 MTM Contracted Rates Cheat Sheet</h3>'
    body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
    body += '<tr style="background-color: #ebf5fb;"><th>Counties</th><th>Base Rate</th><th>Est. 20mi RT Payout</th></tr>'
    for county, rate in sorted(COUNTY_BASE_RATES.items(), key=lambda x: x[1], reverse=True):
        est_rt = (rate + ((20 - MILEAGE_BAND_LIMIT) * MTM_MILEAGE_RATE)) * 2
        body += f"<tr><td>{county}</td><td>${rate:.2f}</td><td style='color:green;'><b>${est_rt:.2f}</b></td></tr>"
    body += '</table>'

    # --- 🏆 SECTION: TOP STRATEGIC ROUTES ---
    if top_routes:
        body += f'<h3 style="color: #8e44ad; border-bottom: 2px solid #8e44ad; margin-top: 25px;">🏆 Top Strategic Routes</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
        body += '<tr style="background-color: #8e44ad; color: white;"><th>Date</th><th>Hub</th><th>Broker</th><th>Jobs</th><th>Shift</th><th>Rev/Hr</th><th>Total</th><th>Route Flow</th></tr>'
        for r in top_routes:
            body += f"<tr><td>{r['Date']}</td><td>{r['Hub']}</td><td><b>{r.get('Broker','MTM')}</b></td><td style='text-align:center;'>{r.get('Job Count','?')}</td><td>{r.get('Shift Length (Hrs)','0')}h</td><td style='color:green;'><b>${float(r['Revenue/Hour']):.2f}</b></td><td><b>${float(r['Total Revenue']):.2f}</b></td><td style='font-size:10px;'>{r.get('Route Description','N/A')}</td></tr>"
        body += '</table>'

    # --- 📅 SECTION: FULL DAY ROUTES (5+ hrs, 3+ jobs) ---
    full_day_routes = []
    if os.path.exists(ROUTES_FILE):
        try:
            fd_df = pd.read_csv(ROUTES_FILE)
            fd_df = fd_df[
                (fd_df['Shift Length (Hrs)'] >= 5.0) &
                (fd_df['Job Count'] >= 3) &
                (fd_df['Revenue/Hour'] >= 39.0)
            ]
            fd_df['Date_Obj'] = pd.to_datetime(fd_df['Date'])
            full_day_routes = fd_df.sort_values(
                by=['Date_Obj', 'Hub', 'Total Revenue'], ascending=[True, True, False]
            ).to_dict('records')
        except: pass

    if full_day_routes:
        body += '<h3 style="color: #1a5276; border-bottom: 2px solid #1a5276; margin-top: 25px;">📅 Full Day Routes (Standalone Driver Day)</h3>'
        body += '<p style="font-size: 11px; color: #555; margin-top: -10px;">Routes with 3+ jobs and 5+ hour shift a driver can run from scratch — grouped by hub.</p>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
        body += '<tr style="background-color: #1a5276; color: white;"><th>Date</th><th>Hub</th><th>Broker</th><th>Jobs</th><th>Shift</th><th>Rev/Hr</th><th>Total $</th><th>Route Flow</th></tr>'
        current_hub = None
        for r in full_day_routes:
            hub = r.get('Hub', '')
            row_bg = '#d6eaf8' if hub != current_hub else 'white'
            current_hub = hub
            body += (
                f"<tr style='background-color:{row_bg};'>"
                f"<td>{r['Date']}</td>"
                f"<td><b>{hub}</b></td>"
                f"<td>{r.get('Broker', 'MTM')}</td>"
                f"<td style='text-align:center;'>{r.get('Job Count', '?')}</td>"
                f"<td>{r.get('Shift Length (Hrs)', '0')}h</td>"
                f"<td style='color:green;'><b>${float(r['Revenue/Hour']):.2f}</b></td>"
                f"<td><b>${float(r['Total Revenue']):.2f}</b></td>"
                f"<td style='font-size:10px;'>{r.get('Route Description', 'N/A')}</td>"
                f"</tr>"
            )
        body += '</table>'

    # --- 🧩 SECTION: DRIVER EXTENSIONS (Always Visible) ---
    body += '<h3 style="color: #27ae60; border-bottom: 2px solid #27ae60; margin-top: 25px;">🧩 Driver Schedule Extensions</h3>'
    if brandy_matches:
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;"><tr style="background-color: #27ae60; color: white;"><th>Day</th><th>Window</th><th>Broker</th><th>Route</th><th>Est. Price</th></tr>'
        for m in sorted(brandy_matches, key=lambda x: x['SortValue'], reverse=True)[:10]:
            body += f"<tr><td>{m['Day']}</td><td>{m['Window']}</td><td><b>{m.get('Broker', 'MTM')}</b></td><td>{m['Route']}</td><td><b>{m['Price']}</b></td></tr>"
        body += '</table>'
    else:
        body += '<p style="font-size: 11px; color: #666; font-style: italic;">No active driver extensions found in this snapshot.</p>'

    # --- 🚨 SECTION: PRIORITY CLINICS ---
    pattern = '|'.join(priority_keywords)
    priority = df_active[df_active['pickup_address'].str.contains(pattern, case=False, na=False) | df_active['dropoff_address'].str.contains(pattern, case=False, na=False)]
    if not priority.empty:
        body += '<h3 style="color: #c0392b; border-bottom: 2px solid #c0392b; margin-top: 25px;">🚨 Priority Clinics (Active Now)</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size:12px;"><tr style="background-color: #f9e79f;"><th>Date</th><th>Time</th><th>Route</th><th>Broker</th><th>Value</th></tr>'
        for _, row in priority.head(10).iterrows():
            body += f"<tr><td>{row['date']}</td><td>{row['pickup_time']}</td><td>{row['simple_pickup']} ➡ {row['simple_dropoff']}</td><td><b>{row['broker']}</b></td><td><b>Est. ${get_robust_price(row, county_map.get(row['pickup_address'], 'Unknown')):.2f}</b></td></tr>"
        body += '</table>'

    # --- 🔥 SECTION: HOTSPOTS ---
    top_locs = df_active['simple_pickup'].value_counts().head(6)
    if not top_locs.empty:
        body += '<h3 style="color: #d35400; border-bottom: 2px solid #d35400; margin-top: 25px;">🔥 Active Hotspots</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size:12px;"><tr style="background-color: #f6ddcc;"><th>Facility/Address</th><th>Broker</th><th>Active Now</th><th>Est. Active Rev</th></tr>'
        for addr, count in top_locs.items():
            active_trips = df_active[df_active['simple_pickup'] == addr]
            main_broker = active_trips['broker'].mode().get(0, 'MTM')
            total_rev = sum(get_robust_price(t_row, county_map.get(t_row['pickup_address'], 'Unknown')) for _, t_row in active_trips.iterrows())
            body += f"<tr><td>{addr}</td><td><b>{main_broker}</b></td><td><b style='color:green;'>{count} Available</b></td><td style='color:green;'><b>${total_rev:,.2f}</b></td></tr>"
        body += '</table>'

    # --- 🔄 SECTION: WEEKLY RECURRING PATTERNS ---
    df['day_name'] = pd.to_datetime(df['date']).dt.day_name()
    recurring = df.groupby(['day_name', 'pickup_time', 'simple_pickup', 'broker']).size().reset_index(name='count').query('count >= 2').sort_values('count', ascending=False).head(5)
    if not recurring.empty:
        body += '<h3 style="color: #2980b9; border-bottom: 2px solid #2980b9; margin-top: 25px;">🔄 Weekly Recurring Patterns</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;"><tr style="background-color: #ebf5fb;"><th>Day</th><th>Time</th><th>Broker</th><th>Pickup</th><th>Freq</th></tr>'
        for _, row in recurring.iterrows():
            body += f"<tr><td>{row['day_name']}</td><td>{row['pickup_time']}</td><td><b>{row['broker']}</b></td><td>{row['simple_pickup']}</td><td>{row['count']}x</td></tr>"
        body += '</table>'

    body += '</body></html>'
    
    attachment = MAP_FILE_PATH
    if datetime.now().hour == 23 and os.path.exists("market_pulse_chart.png"):
        attachment = "market_pulse_chart.png"
        
    send_email(subject, body, is_html=True, attachment_path=attachment)
    conn.close()

if __name__ == "__main__": analyze_and_report()