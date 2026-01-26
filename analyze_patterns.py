import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from email_handler import send_email
from stitch_route import analyze_driver_schedule
import warnings
import os
import re

warnings.filterwarnings('ignore')

DB_PATH = 'data/nemt_data.db'
CLINICS_FILE = 'clinics.txt'
# 📎 MAP FILE PATH (Explicitly defined)
MAP_FILE_PATH = 'nemt_war_room.html'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_priority_keywords():
    default = ["DaVita", "Fresenius", "Dialysis", "Cancer", "Radiation"]
    if not os.path.exists(CLINICS_FILE): return default
    try:
        with open(CLINICS_FILE, 'r') as f:
            keywords = [line.strip() for line in f if line.strip()]
        return keywords if keywords else default
    except: return default

def smart_clean_addr(addr):
    if not addr: return "Unknown"
    if ',' in addr: return addr.split(',')[0].strip()
    parts = addr.split()
    if len(parts) > 3 and parts[-1].isdigit(): 
        parts.pop() 
        return " ".join(parts[:4])
    return addr

def analyze_and_report():
    print("📊 Starting Analysis v7.4 (Golden Master: Time Fix + Attachments)...")
    priority_keywords = load_priority_keywords()
    conn = get_db_connection()
    
    try:
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return

    if df.empty:
        print("   ⚠️ Database is empty.")
        return

    # --- CLEANING & UNIFICATION ---
    df['dt_date'] = pd.to_datetime(df['date'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # ✅ FIX: Use 'last_seen' for accurate Scan Time reporting
    if 'last_seen' in df.columns:
        df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')
        scan_time_col = 'last_seen'
    else:
        df['last_seen'] = df['timestamp']
        scan_time_col = 'timestamp'

    df['broker'] = df['broker'].fillna('MTM')
    df['payout'] = pd.to_numeric(df['payout'], errors='coerce').fillna(0.0)
    df['miles'] = pd.to_numeric(df['miles'], errors='coerce').fillna(0.0)

    df['simple_pickup'] = df['pickup_address'].apply(smart_clean_addr)
    df['simple_dropoff'] = df['dropoff_address'].apply(smart_clean_addr)

    # --- FILTERING ---
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 1. DETERMINE LATEST SCAN TIME
    last_run_time = df[scan_time_col].max()
    
    # 2. FRESH CATCH (New trips created in last 45 mins)
    # We still use 'timestamp' here because we want *newly added* trips
    cutoff_time = last_run_time - timedelta(minutes=45)
    fresh_df = df[df['timestamp'] >= cutoff_time].copy()
    
    # FUTURE TRIPS
    df_future = df[df['dt_date'] >= today_dt].copy()
    df_modiv = df_future[df_future['broker'] == 'Modivcare']
    df_mtm = df_future[df_future['broker'] == 'MTM']

    print(f"   🕒 Scan Time: {last_run_time.strftime('%H:%M')}")
    print(f"   🎣 Fresh Catch: {len(fresh_df)} new trips")

    # --- RUN STITCHER ---
    brandy_matches = analyze_driver_schedule()
    stitch_count = len(brandy_matches)

    # --- REPORT GENERATION ---
    subject = f"NEMT Report: {len(fresh_df)} New Trips | {stitch_count} Shift Matches"
    
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background-color: #2c3e50; color: white; padding: 15px;">
            <h2 style="margin:0;">🚀 NEMT Commander v7.4</h2>
            <p style="margin:5px 0 0 0;">Report for {today_dt.strftime('%A, %B %d')} | Scan: {last_run_time.strftime('%I:%M %p')}</p>
        </div>
        
        <div style="background-color: #f1c40f; padding: 10px; font-size: 14px; font-weight: bold; border-bottom: 2px solid #f39c12;">
            📎 MAP ATTACHED: Open the 'nemt_war_room.html' file attached to this email.
        </div>
    """

    # SECTION A: BRANDY'S MATCHES
    if stitch_count > 0:
        body += f"""
        <div style="padding: 15px; background-color: #d5f5e3; border: 1px solid #2ecc71; margin-top: 15px;">
            <h3 style="margin:0; color: #27ae60;">🧩 Driver Schedule Matches (Brandy)</h3>
            <p style="margin:5px 0;">Found <b>{stitch_count}</b> trips that fit her gaps/overtime.</p>
        </div>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px; margin-top: 10px;">
            <tr style="background-color: #27ae60; color: white;"><th>Type</th><th>Day</th><th>Window</th><th>Trip</th><th>Route</th><th>Est.</th></tr>
        """
        brandy_matches.sort(key=lambda x: x['SortValue'], reverse=True)
        for m in brandy_matches[:8]:
            body += f"<tr><td><b>{m['Type']}</b></td><td>{m['Day']}</td><td>{m['Window']}</td><td>{m['Trip Time']}</td><td>{m['Route']}</td><td><b>{m['Price']}</b></td></tr>"
        body += "</table><br>"

    # SECTION B: THE FRESH CATCH
    if not fresh_df.empty:
        body += f"""
        <h3 style="color: #2980b9; border-bottom: 2px solid #2980b9;">🎣 Fresh Catch ({len(fresh_df)} New Trips)</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <tr style="background-color: #d4e6f1;"><th>Broker</th><th>Date</th><th>Route</th><th>Est.</th></tr>
        """
        for _, row in fresh_df.sort_values('dt_date').head(10).iterrows():
            val = f"${row.get('payout', 0):.2f}" if row['broker'] == 'Modivcare' else f"{row['miles']} mi"
            bg = "#eafaf1" if row['broker'] == 'Modivcare' else "#ffffff"
            body += f"<tr style='background-color: {bg};'><td><b>{row['broker']}</b></td><td>{row['date']}</td><td>{row['simple_pickup']} ➡ {row['simple_dropoff']}</td><td>{val}</td></tr>"
        body += "</table>"

    # SECTION C: HIGH VOLUME (Preserved)
    top_locs = df_future['simple_pickup'].value_counts().head(6)
    if not top_locs.empty:
        body += f"""
        <h3 style="color: #d35400; border-bottom: 2px solid #d35400;">🔥 High Volume Locations</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f6ddcc;"><th>Facility/Address</th><th>Total</th><th>Breakdown</th></tr>
        """
        for addr, total in top_locs.items():
            if total < 2: continue 
            mtm_count = len(df_future[(df_future['simple_pickup'] == addr) & (df_future['broker'] == 'MTM')])
            mod_count = len(df_future[(df_future['simple_pickup'] == addr) & (df_future['broker'] == 'Modivcare')])
            breakdown = []
            if mtm_count: breakdown.append(f"{mtm_count} MTM")
            if mod_count: breakdown.append(f"{mod_count} Modiv")
            
            body += f"<tr><td>{addr}</td><td><strong>{total}</strong></td><td>{', '.join(breakdown)}</td></tr>"
        body += "</table>"

    # SECTION D: MODIVCARE REVENUE (Preserved)
    if not df_modiv.empty:
        body += f"""
        <h3 style="color: #27ae60; border-bottom: 2px solid #27ae60;">💰 Active Modivcare Pipeline</h3>
        <p><strong>Total Value:</strong> ${df_modiv['payout'].sum():,.2f} | <strong>Count:</strong> {len(df_modiv)} Trips</p>
        """

    # SECTION E: RECURRING (Preserved)
    df_future['day_name'] = df_future['dt_date'].dt.day_name()
    pattern_grp = df_future.groupby(['day_name', 'pickup_time', 'simple_pickup', 'broker']).size()
    recurring = pattern_grp[pattern_grp >= 2].sort_values(ascending=False).head(5)

    if not recurring.empty:
        body += """<h3 style="color: #8e44ad; border-bottom: 2px solid #8e44ad;">🔄 Recurring Patterns</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">
        <tr style="background-color: #f4ecf7;"><th>Day</th><th>Time</th><th>Pickup</th><th>Freq</th></tr>"""
        for idx, count in recurring.items():
            body += f"<tr><td>{idx[0]}</td><td>{idx[1]}</td><td>{idx[2]}</td><td>{count}x</td></tr>"
        body += "</table>"

    # SECTION F: PRIORITY CLINICS (Preserved)
    pattern = '|'.join(priority_keywords)
    mask = df_future['pickup_address'].str.contains(pattern, case=False, na=False) | \
           df_future['dropoff_address'].str.contains(pattern, case=False, na=False)
    priority = df_future[mask].sort_values('dt_date')

    if not priority.empty:
        body += f"""
        <h3 style="color: #c0392b; border-bottom: 2px solid #c0392b;">🚨 Priority Clinics ({len(priority)} Matches)</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size:12px;">
            <tr style="background-color: #f9e79f;"><th>Date</th><th>Route</th><th>Broker</th></tr>
        """
        for _, row in priority.head(8).iterrows():
            route = f"{row['simple_pickup']} ➡ {row['simple_dropoff']}"
            body += f"<tr><td>{row['date']}</td><td>{route}</td><td><strong>{row['broker']}</strong></td></tr>"
        body += "</table>"

    # SECTION G: MTM FORECAST (Preserved)
    if not df_mtm.empty:
        vol = df_mtm['date'].value_counts().sort_index().head(7)
        body += f"""
        <h3 style="color: #2980b9;">🌊 MTM Volume Forecast</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 50%;">
            <tr style="background-color: #ebf5fb;"><th>Date</th><th>Count</th></tr>
        """
        for d, c in vol.items():
            body += f"<tr><td>{d}</td><td>{c}</td></tr>"
        body += "</table>"

    body += "</body></html>"
    
    # SEND THE EMAIL WITH THE ATTACHMENT
    print("📧 Sending Report...")
    # ✅ PASSING ATTACHMENT PATH HERE
    send_email(subject, body, is_html=True, attachment_path=MAP_FILE_PATH)
    print("✅ Done.")

if __name__ == "__main__":
    analyze_and_report()