import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from email_handler import send_email
from map_updater import MAP_URL
from stitch_route import analyze_driver_schedule
from regular_riders import get_regular_rider_alerts
from springfield_dispatch import get_springfield_dispatch, get_springfield_summary
import warnings
import os
import json

warnings.filterwarnings('ignore')

# CONFIG
from config import get_logger
log = get_logger(__name__)

from config import (DB_PATH, CLINICS_FILE, ROUTES_FILE, EXCLUDED_COUNTIES,
                    CITY_COUNTY_MAP, MAX_SHIFT_HOURS, MIN_PROFIT_PER_HOUR)
MAP_FILE_PATH = 'nemt_war_room.html'
PULSE_FILE = 'data/market_pulse.csv'
STRICT_MAX_HOURS = MAX_SHIFT_HOURS  # local alias
from mtm_rates import MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT, STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE, COUNTY_BASE_RATES

EMAIL_STATE_FILE = 'data/email_state.json'
EMAIL_MIN_INTERVAL_HOURS = 2


def _load_email_state():
    try:
        with open(EMAIL_STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_sent": None, "last_new_trip_time": None}


def _save_email_state(last_sent, last_new_trip_time):
    os.makedirs('data', exist_ok=True)
    with open(EMAIL_STATE_FILE, 'w') as f:
        json.dump({
            "last_sent": last_sent.isoformat() if last_sent else None,
            "last_new_trip_time": last_new_trip_time.isoformat() if last_new_trip_time else None,
        }, f)


def _should_send_email(newest_trip_time, has_routes, has_rider_alerts):
    state = _load_email_state()
    now = datetime.now()

    last_sent = datetime.fromisoformat(state["last_sent"]) if state["last_sent"] else None
    last_new_trip_time = datetime.fromisoformat(state["last_new_trip_time"]) if state["last_new_trip_time"] else None

    has_new_trips = (newest_trip_time is not None) and (
        last_new_trip_time is None or newest_trip_time > last_new_trip_time
    )
    time_ok = last_sent is None or (now - last_sent) >= timedelta(hours=EMAIL_MIN_INTERVAL_HOURS)

    if has_rider_alerts:
        return True, has_new_trips, newest_trip_time
    if (has_new_trips or has_routes) and time_ok:
        return True, has_new_trips, newest_trip_time
    return False, has_new_trips, newest_trip_time


def get_db_connection():
    if os.path.exists(DB_PATH): return sqlite3.connect(DB_PATH, timeout=30)
    return sqlite3.connect('trips.db', timeout=30)

def load_priority_keywords():
    default = ["DaVita", "Fresenius", "Dialysis", "Cancer", "Radiation"]
    if not os.path.exists(CLINICS_FILE): return default
    try:
        with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        log.warning(f"Failed to load priority keywords from {CLINICS_FILE}: {e}")
        return default

def smart_clean_addr(addr):
    if not addr: return "Unknown"
    return addr.split(',')[0].strip() if ',' in addr else addr[:30]

def get_robust_price(row, cached_county="Unknown"):
    if row.get('broker') == 'Modivcare':
        try: return float(row.get('payout', 0))
        except Exception as e:
            log.warning(f"Modivcare payout parse failed for trip at {row.get('pickup_address', '?')}: {e}")
            return 0.0
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
    except Exception as e:
        log.warning(f"Price estimate failed for trip at {row.get('pickup_address', '?')}: {e}")
        return 0.0

def track_market_pulse(active_count):
    now = datetime.now()
    new_row = {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "count": active_count, "hour": now.hour}
    if not os.path.exists("data"): os.makedirs("data")
    try: pd.DataFrame([new_row]).to_csv(PULSE_FILE, mode='a', header=not os.path.exists(PULSE_FILE), index=False)
    except Exception as e: log.warning(f"Failed to write market pulse to {PULSE_FILE}: {e}")

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
    except Exception as e:
        log.warning(f"Market pulse analysis failed: {e}")
        return "Analyzing..."

def analyze_and_report():
    print("📊 Generating COMPREHENSIVE Strategic Report v12.4 (Phase 1 Clean)...")
    
    # 🛠 SELF-HEALING: Clear stuck browser locks
    os.system(f"rm -rf {os.path.expanduser('~')}/nemt-scraper/user_data/Default/SingletonLock 2>/dev/null")
    
    map_link = MAP_URL

    priority_keywords = load_priority_keywords()
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        cache_df = pd.read_sql_query("SELECT address, county FROM geo_cache", conn)
        county_map = dict(zip(cache_df['address'], cache_df['county']))
    except Exception as e:
        log.error(f"Database read failed: {e}")
        return

    if df.empty: return

    # --- 🛡️ APPLY CHICAGO EXCLUSION ZONE ---
    def is_chicago_area(addr):
        if not isinstance(addr, str): return False
        if county_map.get(addr, 'Unknown') in EXCLUDED_COUNTIES: return True
        addr_lower = addr.lower()
        if 'chicago' in addr_lower and 'il ' in addr_lower: return True
        return False

    df = df[~df['pickup_address'].apply(is_chicago_area) & ~df['dropoff_address'].apply(is_chicago_area)]

    if df.empty:
        print("⚠️ No trips remaining after filtering Chicago area.")
        return

    # --- 🟢 SNAPSHOT INTEGRITY: Define ACTIVE trips ---
    time_col = 'last_seen' if 'last_seen' in df.columns else 'timestamp'
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    latest_scan_time = df[time_col].max()
    
    # Snapshot Pulse (Last 120 Mins)
    df_active = df[df[time_col] >= (latest_scan_time - timedelta(minutes=150))].copy()
    pulse_count = len(df_active)
    track_market_pulse(pulse_count)

    for d in [df_active, df]:
        d['broker'] = d['broker'].fillna('MTM')
        d['simple_pickup'] = d['pickup_address'].apply(smart_clean_addr)
        d['simple_dropoff'] = d['dropoff_address'].apply(smart_clean_addr)

    # 1. 🏆 TOP STRATEGIC & FULL DAY ROUTES (Merged)
    top_routes = []
    if os.path.exists(ROUTES_FILE):
        try:
            r_df = pd.read_csv(ROUTES_FILE)
            r_df = r_df[(r_df['Shift Length (Hrs)'] <= STRICT_MAX_HOURS) & (r_df['Revenue/Hour'] >= MIN_PROFIT_PER_HOUR)]
            r_df['Date_Obj'] = pd.to_datetime(r_df['Date'])
            # Grouping visually by sorting Date -> Hub -> Revenue
            top_routes = r_df.sort_values(by=['Date_Obj', 'Hub', 'Total Revenue'], ascending=[True, True, False]).to_dict('records')
        except Exception as e:
            log.warning(f"Failed to load routes from {ROUTES_FILE}: {e}")

    brandy_matches = analyze_driver_schedule()
    regular_rider_alerts = get_regular_rider_alerts()
    conn.close()  # release DB lock — all data already loaded into memory above
    market_status = analyze_market_pulse()
    refresh_time = latest_scan_time.strftime('%H:%M')
    subject = f"NEMT Command | {len(top_routes)} Shifts | {market_status}"

    map_btn = f'<a href="{map_link}" style="background:#2980b9; color:white; padding:8px 16px; border-radius:4px; text-decoration:none; font-weight:bold; margin-left:10px;">🗺️ Open Live Map</a>' if map_link else ''

    body = f"""<html><body style="font-family: Arial, sans-serif; color: #333;">
    <div style="background-color: #2c3e50; color: white; padding: 15px;">
        <h2 style="margin:0;">🚀 NEMT Commander v12.4 {map_btn}</h2>
        <p style="margin:5px 0 0 0;">Market: {market_status} | {pulse_count} active trips (Excl. Chicago) | Refreshed: {refresh_time}</p>
    </div>"""

    # --- 💰 SECTION: MTM CONTRACTED RATES ---
    body += '<h3 style="color: #2980b9; border-bottom: 2px solid #2980b9; margin-top: 25px;">💰 MTM Contracted Rates Cheat Sheet</h3>'
    body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
    body += '<tr style="background-color: #2980b9; color: white;"><th>Counties</th><th>Base Rate</th><th>Est. 20mi RT Payout</th></tr>'
    for county, rate in sorted(COUNTY_BASE_RATES.items(), key=lambda x: x[1], reverse=True):
        est_rt = (rate + ((20 - MILEAGE_BAND_LIMIT) * MTM_MILEAGE_RATE)) * 2
        body += f"<tr><td>{county}</td><td>${rate:.2f}</td><td style='color:green;'><b>${est_rt:.2f}</b></td></tr>"
    body += '</table>'

    # --- 🏆 SECTION: TOP STRATEGIC & FULL DAY ROUTES (split by model) ---
    traditional_routes = [r for r in top_routes if r.get('Model', 'Traditional') == 'Traditional']
    clinic_routes = [r for r in top_routes if r.get('Model') == 'Clinic']

    def render_route_table(routes, header_color, title, subtitle):
        out = f'<h3 style="color: {header_color}; border-bottom: 2px solid {header_color}; margin-top: 25px;">{title}</h3>'
        out += f'<p style="font-size: 11px; color: #555; margin-top: -10px;">{subtitle}</p>'
        out += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
        out += f'<tr style="background-color: {header_color}; color: white;"><th>Date</th><th>Hub</th><th>Top County</th><th>Broker</th><th>Jobs</th><th>Shift</th><th>Rev/Hr</th><th>Total</th><th>Route Flow</th></tr>'
        current_hub = None
        for r in routes:
            hub = r.get('Hub', '')
            row_bg = '#f0f0f0' if hub != current_hub else 'white'
            current_hub = hub
            shift_len = float(r.get('Shift Length (Hrs)', 0))
            shift_display = f"<b>{shift_len}h</b>" if shift_len >= 5.0 else f"{shift_len}h"
            out += f"<tr style='background-color:{row_bg};'><td>{r['Date']}</td><td><b>{hub}</b></td><td>{r.get('Top County','?')}</td><td>{r.get('Broker','MTM')}</td><td style='text-align:center;'>{r.get('Job Count','?')}</td><td>{shift_display}</td><td style='color:green;'><b>${float(r['Revenue/Hour']):.2f}</b></td><td><b>${float(r['Total Revenue']):.2f}</b></td><td style='font-size:10px;'>{r.get('Route Description','N/A')}</td></tr>"
        out += '</table>'
        return out

    if traditional_routes:
        body += render_route_table(
            traditional_routes, '#8e44ad',
            '🏆 Traditional Routes',
            'Standard medical transport — 1-hour appointment buffer, round trip per patient.'
        )

    if clinic_routes:
        body += render_route_table(
            clinic_routes, '#e67e22',
            '💊 Clinic Routes (Multi-Load)',
            'Substance/dialysis clinics — multi-load to same clinic, 5-min appointment, flexible morning window.'
        )

    # --- 🏙️ SECTION: SPRINGFIELD DISPATCH ---
    springfield_routes = get_springfield_dispatch()
    if springfield_routes:
        body += '<h3 style="color: #1a6b3c; border-bottom: 2px solid #1a6b3c; margin-top: 25px;">🏙️ Springfield Dispatch</h3>'
        body += get_springfield_summary()
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
        body += '<tr style="background-color: #1a6b3c; color: white;"><th>Date</th><th>Driver</th><th>Priority</th><th>Model</th><th>Jobs</th><th>Shift</th><th>Rev/Hr</th><th>Total</th><th>Top County</th><th>Route Flow</th></tr>'
        for r in springfield_routes:
            shift_len = float(r.get('Shift Length (Hrs)', 0))
            shift_display = f"<b>{shift_len}h</b>" if shift_len >= 5.0 else f"{shift_len}h"
            body += f"<tr><td>{r['Date']}</td><td><b>{r['Driver']}</b></td><td>{r['Priority']}</td><td>{r['Model']}</td><td style='text-align:center;'>{r['Job Count']}</td><td>{shift_display}</td><td style='color:green;'><b>${float(r['Revenue/Hour']):.2f}</b></td><td><b>${float(r['Total Revenue']):.2f}</b></td><td>{r['Top County']}</td><td style='font-size:10px;'>{r['Route Description']}</td></tr>"
        body += '</table>'

    # --- ⚡ SECTION: REGULAR RIDERS ON MARKETPLACE ---
    if regular_rider_alerts:
        body += '<h3 style="color: #e67e22; border-bottom: 3px solid #e67e22; margin-top: 25px;">⚡ REGULAR RIDERS ON MARKETPLACE — ACCEPT NOW</h3>'
        body += '<p style="font-size: 11px; color: #e67e22; font-weight: bold; margin-top: -10px;">These are your standing-order riders that have been placed back on the marketplace. Accept immediately before another provider takes them.</p>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">'
        body += '<tr style="background-color: #e67e22; color: white;"><th>⚡</th><th>Date</th><th>Time</th><th>Pickup Address</th><th>Dropoff</th><th>Miles</th><th>Broker</th></tr>'
        for alert in regular_rider_alerts:
            urgency_badge = '<b style="color:red;">TODAY</b>' if alert['urgency'] == 'TODAY' else 'Upcoming'
            body += f"<tr style='background-color:#fef9e7;'><td>{urgency_badge}</td><td>{alert['date']}</td><td><b>{alert['pickup_time']}</b></td><td><b>{alert['pickup_address']}</b><br><span style='font-size:10px;color:#888;'>Matched: {alert['matched_schedule_address']}</span></td><td>{alert['dropoff_address']}</td><td>{alert['miles']}</td><td>{alert['broker']}</td></tr>"
        body += '</table>'
    else:
        body += '<h3 style="color: #e67e22; border-bottom: 2px solid #e67e22; margin-top: 25px;">⚡ Regular Riders on Marketplace</h3>'
        body += '<p style="font-size: 11px; color: #666; font-style: italic;">✅ No regular rider addresses found on marketplace in this snapshot.</p>'

    # --- 🧩 SECTION: DRIVER EXTENSIONS (Always Visible) ---
    body += '<h3 style="color: #27ae60; border-bottom: 2px solid #27ae60; margin-top: 25px;">🧩 Driver Schedule Extensions</h3>'
    if brandy_matches:
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;"><tr style="background-color: #27ae60; color: white;"><th>Driver</th><th>Day</th><th>Window</th><th>Broker</th><th>Route</th><th>Est. Price</th></tr>'
        for m in sorted(brandy_matches, key=lambda x: x['SortValue'], reverse=True)[:10]:
            body += f"<tr><td><b>{m.get('Driver', 'N/A')}</b></td><td>{m['Day']}</td><td>{m['Window']}</td><td><b>{m.get('Broker', 'MTM')}</b></td><td>{m['Route']}</td><td><b>{m['Price']}</b></td></tr>"
        body += '</table>'
    else:
        body += '<p style="font-size: 11px; color: #666; font-style: italic;">No active driver extensions found in this snapshot.</p>'

    # --- 🚨 SECTION: PRIORITY CLINICS ---
    pattern = '|'.join(priority_keywords)
    priority = df_active[df_active['pickup_address'].str.contains(pattern, case=False, na=False) | df_active['dropoff_address'].str.contains(pattern, case=False, na=False)]
    if not priority.empty:
        body += '<h3 style="color: #c0392b; border-bottom: 2px solid #c0392b; margin-top: 25px;">🚨 Priority Clinics (Active Now)</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size:11px;"><tr style="background-color: #c0392b; color: white;"><th>Date</th><th>Time</th><th>Route</th><th>Broker</th><th>Value</th></tr>'
        for _, row in priority.head(10).iterrows():
            body += f"<tr><td>{row['date']}</td><td>{row['pickup_time']}</td><td>{row['simple_pickup']} ➡️ {row['simple_dropoff']}</td><td><b>{row['broker']}</b></td><td><b>Est. ${get_robust_price(row, county_map.get(row['pickup_address'], 'Unknown')):.2f}</b></td></tr>"
        body += '</table>'

    # --- 🔥 SECTION: HOTSPOTS ---
    top_locs = df_active['simple_pickup'].value_counts().head(6)
    if not top_locs.empty:
        body += '<h3 style="color: #d35400; border-bottom: 2px solid #d35400; margin-top: 25px;">🔥 Active Hotspots</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size:11px;"><tr style="background-color: #d35400; color: white;"><th>Facility/Address</th><th>Broker</th><th>Active Now</th><th>Est. Active Rev</th></tr>'
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
        body += '<h3 style="color: #34495e; border-bottom: 2px solid #34495e; margin-top: 25px;">🔄 Weekly Recurring Patterns</h3>'
        body += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;"><tr style="background-color: #34495e; color: white;"><th>Day</th><th>Time</th><th>Broker</th><th>Pickup</th><th>Freq</th></tr>'
        for _, row in recurring.iterrows():
            body += f"<tr><td>{row['day_name']}</td><td>{row['pickup_time']}</td><td><b>{row['broker']}</b></td><td>{row['simple_pickup']}</td><td>{row['count']}x</td></tr>"
        body += '</table>'

    body += '</body></html>'

    # --- 📬 SEND GATE: only email when there is something actionable ---
    newest_trip_time = latest_scan_time if not pd.isnull(latest_scan_time) else None
    should_send, has_new_trips, newest_trip_time = _should_send_email(
        newest_trip_time, bool(top_routes), bool(regular_rider_alerts)
    )

    if should_send:
        send_email(subject, body, is_html=True)
        _save_email_state(
            last_sent=datetime.now(),
            last_new_trip_time=newest_trip_time,
        )
    else:
        print("📭 Email skipped: no new trips, no routes, no rider alerts, or within 2-hour cooldown.")

if __name__ == "__main__": analyze_and_report()