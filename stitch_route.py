import pandas as pd
import sqlite3
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime, timedelta
import warnings
import re
import os

warnings.filterwarnings('ignore')

# 🛠 SETTINGS
DRIVER_FILE = 'driver_schedule.csv'
DB_PATH = 'data/nemt_data.db'
DEPOT_ADDRESS = "506 South St, Effingham, IL 62401"

# CONSTRAINTS
MAX_SHIFT_HOURS = 10.0  
MAX_RADIUS_MILES = 30   
AVG_MPH = 40            
MIN_GAP_HOURS = 0.5     

# 💰 PRICING DATA
MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT = 1.50, 5.0
STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE = 20.00, 20.00

COUNTY_BASE_RATES = {
    "Coles County": 40.00, "Fayette County": 40.00, "Clay County": 40.00,
    "Marion County": 50.00, "Jefferson County": 50.00,
    "Christian County": 35.00, "Macon County": 35.00, "Piatt County": 35.00, "Champaign County": 35.00,
    "Sangamon County": 65.00, "Vermilion County": 65.00, "Edgar County": 40.00, "Clark County": 40.00
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

# 🌍 GEOCODING ENGINE
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]
geolocator = Nominatim(user_agent="jgritter_nemt_stitcher_v11_8", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

def get_db_connection():
    if os.path.exists(DB_PATH): return sqlite3.connect(DB_PATH)
    return sqlite3.connect('trips.db')

def force_illinois_context(addr):
    if not addr: return ""
    if re.search(r'\bIL\b|\bIllinois\b', addr, re.IGNORECASE): return addr
    zip_match = re.search(r'(\d{5})$', addr)
    if zip_match: return addr[:zip_match.start()] + " IL " + addr[zip_match.start():]
    return f"{addr}, Illinois"

def get_lat_lon(conn, address):
    if not isinstance(address, str): return None, None
    clean = address.replace('\n', ' ').strip().replace(', USA', '').strip()
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lon FROM geo_cache WHERE address = ?", (clean,))
    res = cursor.fetchone()
    if res and res[0] != 0: return res
    
    try:
        loc = geocode_service(clean, country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if not loc:
            loc = geocode_service(force_illinois_context(clean), country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if loc:
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, ?, ?)", (clean, loc.latitude, loc.longitude))
            conn.commit()
            return loc.latitude, loc.longitude
    except: pass
    cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, 0, 0)", (clean,))
    conn.commit()
    return None, None

def calculate_manual_price(row):
    if row.get('broker') == 'Modivcare':
        try: return float(row.get('payout', 0))
        except: return 0.0
    try:
        addr = str(row['pickup_address']).lower()
        county = "Unknown"
        for city, c_name in CITY_COUNTY_MAP.items():
            if city in addr:
                county = c_name
                break
        dt_val = row['date'] if isinstance(row['date'], str) else row['date'].strftime('%Y-%m-%d')
        pickup_time = pd.to_datetime(dt_val + ' ' + row['pickup_time'])
        base = COUNTY_BASE_RATES.get(county, STANDARD_BASE_RATE)
        if pickup_time.hour < 6 or pickup_time.hour >= 18: base = max(base, AFTER_HOURS_BASE_RATE)
        miles = float(row.get('miles', 0))
        billable = max(0, miles - MILEAGE_BAND_LIMIT)
        return round((base + (billable * MTM_MILEAGE_RATE)) * 2, 2)
    except: return 0.0

def safe_get_price(row):
    price = calculate_manual_price(row)
    if price == 0:
        try:
            val = float(row.get('payout', 0))
            if val > 0: return val * 2, f"${val*2:.2f}"
        except: pass
        return 0.0, "Check Price"
    return price, f"${price:.2f}"

def analyze_driver_schedule():
    if not os.path.exists(DRIVER_FILE): return []
    print("🧵 Running Multi-Driver Stitcher v11.8 (Final Snapshot Integrity)...")
    conn = get_db_connection()
    depot_coords = get_lat_lon(conn, DEPOT_ADDRESS)
    
    templates = {} 
    try:
        raw_sched = pd.read_csv(DRIVER_FILE)
        raw_sched.columns = raw_sched.columns.str.strip()
        if 'Driver' not in raw_sched.columns: raw_sched['Driver'] = 'Driver'

        for _, row in raw_sched.iterrows():
            try:
                driver = str(row['Driver']).strip()
                dt = pd.to_datetime(row['Date'])
                weekday = dt.weekday()
                pu_coords = get_lat_lon(conn, row['PU Address'])
                do_coords = get_lat_lon(conn, row['DO Address'])
                if driver not in templates: templates[driver] = {}
                if weekday not in templates[driver]: templates[driver][weekday] = []
                templates[driver][weekday].append({
                    'pu_time_str': row['Pick up time'], 'do_time_str': row['Drop off time'],
                    'pu_addr': row['PU Address'], 'do_addr': row['DO Address'],
                    'pu_coords': pu_coords, 'do_coords': do_coords, 'mileage': float(row['Mileage'])
                })
            except: continue
        for driver in templates:
            for d in templates[driver]:
                templates[driver][d].sort(key=lambda x: pd.to_datetime(x['pu_time_str']).time())
    except: conn.close(); return []

    # --- 🟢 HOURLY SYNC PROTECTION: Kills Ghost Trips ---
    market_df = pd.read_sql_query("SELECT * FROM trips", conn)
    time_col = 'last_seen' if 'last_seen' in market_df.columns else 'timestamp'
    market_df[time_col] = pd.to_datetime(market_df[time_col], errors='coerce')
    
    # Identify the latest possible update from the scraper
    latest_db_refresh = market_df[time_col].max()
    
    # SNAPSHOT: Only trust trips refreshed in the last 120 minutes.
    # This prevents the 'Ghosting' but allows for cron job gaps.
    market_df = market_df[market_df[time_col] >= (latest_db_refresh - timedelta(minutes=120))]

    market_df['dt_date'] = pd.to_datetime(market_df['date'], errors='coerce').dt.date
    today = datetime.now().date()
    # Filter for today and all available future dates in the snapshot
    market_df = market_df[market_df['dt_date'] >= today]

    if market_df.empty: 
        print("⚠️ Marketplace Snapshot is empty. No fresh trips found.")
        conn.close(); return []
        
    unique_dates = sorted(market_df['dt_date'].unique())
    opportunities = []

    for driver, schedule in templates.items():
        for current_date in unique_dates:
            weekday = current_date.weekday()
            if weekday not in schedule: continue
            
            day_trips = schedule[weekday]
            todays_schedule = []
            for t in day_trips:
                todays_schedule.append({**t, 
                    'pu_dt': pd.to_datetime(f"{current_date} {t['pu_time_str']}"),
                    'do_dt': pd.to_datetime(f"{current_date} {t['do_time_str']}")
                })

            todays_schedule.sort(key=lambda x: x['pu_dt'])
            daily_candidates = market_df[market_df['dt_date'] == current_date].copy()
            day_name, date_str = current_date.strftime('%A'), current_date.strftime('%m/%d')

            # --- PART 1: GAPS ---
            for i in range(len(todays_schedule) - 1):
                trip_a, trip_b = todays_schedule[i], todays_schedule[i+1]
                t_free = trip_a['pu_dt'] + timedelta(hours=(trip_a['mileage'] / AVG_MPH) + 0.25)
                if (trip_b['pu_dt'] - t_free).total_seconds() / 3600 < MIN_GAP_HOURS: continue
                if not trip_a['do_coords'] or not trip_a['do_coords'][0]: continue

                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(str(opp['date']) + ' ' + opp['pickup_time'])
                        sim_start = t_free.replace(hour=opp_ts.hour, minute=opp_ts.minute)
                        if sim_start < (t_free + timedelta(minutes=15)): continue
                        opp_pu = get_lat_lon(conn, opp['pickup_address'])
                        if not opp_pu or geodesic(trip_a['do_coords'], opp_pu).miles > MAX_RADIUS_MILES: continue
                        opp_do = get_lat_lon(conn, opp['dropoff_address'])
                        loop_hours = ((geodesic(trip_a['do_coords'], opp_pu).miles + geodesic(opp_pu, opp_do).miles + geodesic(opp_do, trip_a['do_coords']).miles) / AVG_MPH) + 0.25
                        if sim_start + timedelta(hours=loop_hours) < (trip_b['pu_dt'] - timedelta(minutes=15)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": f"🧩 GAP ({driver})", 
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}", 
                                "Window": f"{t_free.strftime('%H:%M')}-{trip_b['pu_dt'].strftime('%H:%M')}", 
                                "Trip Time": opp['pickup_time'], 
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡ {opp['dropoff_address'].split(',')[0]}", 
                                "Trip ID": opp.get('trip_id', 'N/A'), 
                                "Price": display_price, "SortValue": sort_val
                            })
                    except: continue

            # --- PART 2: EXTENSIONS ---
            last_trip = todays_schedule[-1]
            t_free = last_trip['pu_dt'] + timedelta(hours=(last_trip['mileage'] / AVG_MPH) + 0.25)
            shift_start = todays_schedule[0]['pu_dt']
            hard_stop = shift_start + timedelta(hours=MAX_SHIFT_HOURS)

            if t_free < hard_stop and last_trip['do_coords'] and last_trip['do_coords'][0]:
                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(str(opp['date']) + ' ' + opp['pickup_time'])
                        sim_start = t_free.replace(hour=opp_ts.hour, minute=opp_ts.minute)
                        if sim_start < (t_free + timedelta(minutes=15)): continue
                        
                        opp_pu = get_lat_lon(conn, opp['pickup_address'])
                        if not opp_pu or geodesic(last_trip['do_coords'], opp_pu).miles > MAX_RADIUS_MILES: continue
                        opp_do = get_lat_lon(conn, opp['dropoff_address'])
                        
                        t_keys_out = sim_start + timedelta(hours=(geodesic(opp_pu, opp_do).miles / AVG_MPH) + (geodesic(opp_do, depot_coords).miles / AVG_MPH) + 0.25)
                        if t_keys_out <= (hard_stop + timedelta(minutes=45)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": f"➕ EXTENSION ({driver})", 
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}", 
                                "Window": f"After {t_free.strftime('%H:%M')}", 
                                "Trip Time": opp['pickup_time'], 
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡ {opp['dropoff_address'].split(',')[0]}", 
                                "Trip ID": opp.get('trip_id', 'N/A'), 
                                "Price": display_price, "SortValue": sort_val
                            })
                    except: continue

    conn.close()
    if opportunities:
        pd.DataFrame(opportunities).sort_values(['Day', 'SortValue'], ascending=[True, False]).to_csv("brandy_overtime.csv", index=False)
    return opportunities

if __name__ == "__main__": analyze_driver_schedule()