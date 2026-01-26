import sqlite3
import pandas as pd
from datetime import datetime
from email_handler import send_email
import warnings
import os
import re

warnings.filterwarnings('ignore')

DB_PATH = 'data/nemt_data.db'
CLINICS_FILE = 'clinics.txt'

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_priority_keywords():
    """Reads the external clinics.txt file."""
    default = ["DaVita", "Fresenius", "Dialysis", "Cancer"]
    if not os.path.exists(CLINICS_FILE):
        return default
    try:
        with open(CLINICS_FILE, 'r') as f:
            keywords = [line.strip() for line in f if line.strip()]
        return keywords if keywords else default
    except: return default

def analyze_and_report():
    print("📊 Starting Analysis v5.4 (Broker Identification Update)...")
    priority_keywords = load_priority_keywords()
    conn = get_db_connection()
    
    try:
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return

    # --- CLEANING & UNIFICATION ---
    df['dt_date'] = pd.to_datetime(df['date'], errors='coerce')
    df['broker'] = df['broker'].fillna('MTM')
    df['payout'] = pd.to_numeric(df['payout'], errors='coerce').fillna(0.0)

    def smart_clean_addr(addr):
        if not addr: return "Unknown"
        # 1. If it has a comma (MTM style), take the first part
        if ',' in addr:
            return addr.split(',')[0].strip()
        
        # 2. If no comma (Modivcare style: "123 Main St City Zip")
        # We try to strip the last few words if they look like Zip/City
        parts = addr.split()
        if len(parts) > 3:
            if parts[-1].isdigit(): parts.pop() # Remove Zip
            return " ".join(parts[:4]) # approximate "123 Main St South"
        return addr

    df['simple_pickup'] = df['pickup_address'].apply(smart_clean_addr)
    df['simple_dropoff'] = df['dropoff_address'].apply(smart_clean_addr)

    # --- FILTERING ---
    today_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # MASTER LIST (Includes BOTH Modivcare and MTM)
    df_future = df[df['dt_date'] >= today_dt].copy()
    
    df_modiv = df_future[df_future['broker'] == 'Modivcare']
    df_mtm = df_future[df_future['broker'] == 'MTM']

    # --- REPORT GENERATION ---
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="background-color: #2c3e50; color: white; padding: 15px;">
            <h2 style="margin:0;">🚛 NEMT Intelligence v5.4</h2>
            <p style="margin:5px 0 0 0;">Report for {today_dt.strftime('%A, %B %d')}</p>
        </div>
    """

    # --- 1. MODIVCARE REVENUE ---
    if not df_modiv.empty:
        body += f"""
        <h3 style="color: #27ae60; border-bottom: 2px solid #27ae60;">💰 Modivcare Revenue ({len(df_modiv)} Trips)</h3>
        <p><strong>Total Value:</strong> ${df_modiv['payout'].sum():,.2f} | <strong>Avg:</strong> ${df_modiv['payout'].mean():,.2f}</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <tr style="background-color: #eafaf1;"><th>Date</th><th>Time</th><th>Route</th><th>Payout</th></tr>
        """
        for _, row in df_modiv.nlargest(8, 'payout').iterrows():
            route = f"{row['simple_pickup']} ➡️ {row['simple_dropoff']}"
            body += f"<tr><td>{row['date']}</td><td>{row['pickup_time']}</td><td>{route}</td><td><strong>${row['payout']:.2f}</strong></td></tr>"
        body += "</table>"

    # --- 2. UPCOMING HIGH VOLUME (UNIFIED) ---
    top_locs = df_future['simple_pickup'].value_counts().head(6)
    
    if not top_locs.empty:
        body += f"""
        <h3 style="color: #d35400; border-bottom: 2px solid #d35400;">🔥 Upcoming High-Volume Pickups</h3>
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
            breakdown_str = ", ".join(breakdown)
            
            body += f"<tr><td>{addr}</td><td><strong>{total}</strong></td><td>{breakdown_str}</td></tr>"
        body += "</table>"

    # --- 3. RECURRING PATTERNS (UPDATED) ---
    # Now grouping by BROKER as well
    df['day_name'] = df['dt_date'].dt.day_name()
    pattern_grp = df.groupby(['day_name', 'pickup_time', 'simple_pickup', 'broker']).size()
    recurring = pattern_grp[pattern_grp >= 2].sort_values(ascending=False).head(5)

    if not recurring.empty:
        body += f"""
        <h3 style="color: #8e44ad; border-bottom: 2px solid #8e44ad;">🔄 Weekly Recurring Patterns</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f4ecf7;"><th>Day</th><th>Time</th><th>Pickup</th><th>Broker</th><th>Freq</th></tr>
        """
        for idx, count in recurring.items():
            day, time, pick, broker = idx
            body += f"<tr><td>{day}</td><td>{time}</td><td>{pick}</td><td><strong>{broker}</strong></td><td>{count}x</td></tr>"
        body += "</table>"

    # --- 4. PRIORITY CLINICS (ACTIVE CROSS-REFERENCE) ---
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
        for _, row in priority.head(10).iterrows():
            route = f"{row['simple_pickup']} ➡️ {row['simple_dropoff']}"
            body += f"<tr><td>{row['date']}</td><td>{route}</td><td><strong>{row['broker']}</strong></td></tr>"
        body += "</table>"
    else:
        print("   ℹ️ No priority keywords matched in future trips.")

    # --- 5. MTM VOLUME ---
    if not df_mtm.empty:
        vol = df_mtm['date'].value_counts().sort_index()
        body += f"""
        <h3 style="color: #2980b9;">🌊 MTM Volume Forecast</h3>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
            <tr style="background-color: #ebf5fb;"><th>Date</th><th>Count</th></tr>
        """
        for d, c in vol.items():
            body += f"<tr><td>{d}</td><td>{c}</td></tr>"
        body += "</table>"

    body += "</body></html>"
    
    print("📧 Sending Report...")
    send_email("NEMT Intelligence v5.4", body, is_html=True)
    print("✅ Done.")

if __name__ == "__main__":
    analyze_and_report()
