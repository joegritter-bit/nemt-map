import sqlite3
import pandas as pd
from datetime import datetime
import os
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import itertools
import warnings
import re

warnings.filterwarnings('ignore')

# --- 🛠️ CONFIGURATION ---
DB_PATH = 'data/nemt_data.db'
CLINICS_FILE = 'clinics.txt'
OUTPUT_FILE = 'potential_routes.csv' # MUST match analyze_patterns.py

HUBS = {
    "Effingham": "506 South St, Effingham, IL 62401",
    "Springfield": "Springfield, IL" 
}

# CONSTRAINTS
MIN_TRIPS = 4         # The Density Floor
MAX_CAPACITY = 4      # Van Capacity
MIN_REV_PER_HR = 45.0 # The Profitability Floor
MAX_SHIFT_HOURS = 10.0
AVG_MPH = 40.0

# The Chicago Exclusion Zone
EXCLUDED_COUNTIES = {
    'Cook County', 'DuPage County', 'Kane County', 
    'Lake County', 'McHenry County', 'Will County'
}

# 💰 PRICING DATA
from mtm_rates import MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT, STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE, COUNTY_BASE_RATES

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
geolocator = Nominatim(user_agent="JoeNEMT_Bot_v1_route_optimizer", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.1, max_retries=3, error_wait_seconds=2)

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_clinics():
    if not os.path.exists(CLINICS_FILE): return []
    with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip()]

def get_lat_lon(conn, address):
    if not isinstance(address, str): return None, None
    clean = address.replace('\n', ' ').strip().replace(', USA', '').strip()
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lon FROM geo_cache WHERE address = ?", (clean,))
    res = cursor.fetchone()
    if res and res[0] != 0: return res
    
    try:
        loc = geocode_service(clean, country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if loc:
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, ?, ?)", (clean, loc.latitude, loc.longitude))
            return loc.latitude, loc.longitude
    except: pass
    return None, None

def calculate_trip_price(trip, pickup_addr):
    if trip.get('broker') == 'Modivcare':
        try: return float(trip.get('payout', 0))
        except: return 0.0
    
    county = "Unknown"
    addr_lower = str(pickup_addr).lower()
    for city, c_name in CITY_COUNTY_MAP.items():
        if city in addr_lower:
            county = c_name
            break
            
    base = COUNTY_BASE_RATES.get(county, STANDARD_BASE_RATE)
    miles = float(trip.get('miles', 0))
    billable = max(0, miles - MILEAGE_BAND_LIMIT)
    # Return round trip price
    return round((base + (billable * MTM_MILEAGE_RATE)) * 2, 2)

def calculate_route_cluster(trips, hub_coords, hub_name, conn, clinics_list):
    """Calculates a highly efficient multi-load round trip."""
    if not trips: return None

    dropoff_address = trips[0]['dropoff_address']
    dropoff_coords = get_lat_lon(conn, dropoff_address)
    if not dropoff_coords: return None

    total_distance = 0
    total_revenue = 0
    route_steps = [f"[{hub_name}]"]

    # LEG A: Hub -> Pickups -> Clinic
    current_location = hub_coords
    for trip in trips:
        pu_addr = trip['pickup_address']
        pu_coords = get_lat_lon(conn, pu_addr)
        if not pu_coords: return None
        
        total_distance += geodesic(current_location, pu_coords).miles
        current_location = pu_coords
        total_revenue += calculate_trip_price(trip, pu_addr)
        route_steps.append(pu_addr.split(',')[0])

    # Drive to Clinic
    total_distance += geodesic(current_location, dropoff_coords).miles
    route_steps.append(f"🏥 {dropoff_address.split(',')[0]}")

    # WAIT TIME (Clinic Flex)
    is_clinic = any(c in str(dropoff_address).lower() for c in clinics_list)
    wait_hours = 0.083 if is_clinic else 1.0 # 5 mins vs 1 hour

    # LEG B: Clinic -> Dropoffs (Reverse Order) -> Hub
    current_location = dropoff_coords
    for trip in reversed(trips):
        pu_coords = get_lat_lon(conn, trip['pickup_address'])
        total_distance += geodesic(current_location, pu_coords).miles
        current_location = pu_coords
        route_steps.append(trip['pickup_address'].split(',')[0])

    total_distance += geodesic(current_location, hub_coords).miles
    route_steps.append(f"[{hub_name}]")

    total_time_hours = (total_distance / AVG_MPH) + wait_hours + (len(trips) * 0.25) # Drive + Wait + 15 min per load/unload
    
    if total_time_hours == 0: return None
    rev_per_hour = round(total_revenue / total_time_hours, 2)

    return {
        "Date": trips[0]['date'],
        "Hub": hub_name,
        "Broker": trips[0].get('broker', 'MTM'),
        "Job Count": len(trips),
        "Shift Length (Hrs)": round(total_time_hours, 1),
        "Revenue/Hour": rev_per_hour,
        "Total Revenue": round(total_revenue, 2),
        "Start Address": trips[0]['pickup_address'],
        "Route Description": " ➡️ ".join(route_steps)
    }

def optimize_routes():
    print("🚀 Running Strategic Route Optimizer v12.4 (Strict Multi-Loading)...")
    conn = get_db_connection()
    clinics_list = load_clinics()
    
    # 1. Load active trips
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    df['dt_date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
    today = datetime.now().date()
    df = df[df['dt_date'] >= today]
    
    if df.empty:
        print("⚠️ No future trips found to optimize.")
        return

    # 2. Apply Chicago Exclusion Zone
    cache_df = pd.read_sql_query("SELECT address, county FROM geo_cache", conn)
    county_map = dict(zip(cache_df['address'], cache_df['county']))
    
    def is_chicago_area(addr):
        if not isinstance(addr, str): return False
        if county_map.get(addr, 'Unknown') in EXCLUDED_COUNTIES: return True
        if 'chicago' in addr.lower() and 'il ' in addr.lower(): return True
        return False

    df = df[~df['pickup_address'].apply(is_chicago_area) & ~df['dropoff_address'].apply(is_chicago_area)]

    hub_coords = {name: get_lat_lon(conn, addr) for name, addr in HUBS.items()}
    strategic_routes = []

    # 3. Group by Date and exact Dropoff (The Holy Grail of Multi-loading)
    grouped = df.groupby(['date', 'dropoff_address'])
    
    for (route_date, destination), group in grouped:
        trips = group.to_dict('records')
        
        # We ONLY care about clusters of 4 (or exactly the length if it happens to be 3 and incredibly profitable)
        # But per constraints, we enforce MIN_TRIPS (4)
        if len(trips) < MIN_TRIPS:
            continue
            
        # If there are exactly 4, or more than 4, chunk them into groups of 4
        for i in range(0, len(trips), MAX_CAPACITY):
            cluster = trips[i:i + MAX_CAPACITY]
            if len(cluster) < MIN_TRIPS:
                continue # Ignore leftover fragments smaller than 4

            for hub_name, coords in hub_coords.items():
                if coords:
                    route_data = calculate_route_cluster(cluster, coords, hub_name, conn, clinics_list)
                    
                    # 4. Apply The Profitability Floor and Shift Limits
                    if route_data and route_data['Revenue/Hour'] >= MIN_REV_PER_HR and route_data['Shift Length (Hrs)'] <= MAX_SHIFT_HOURS:
                        strategic_routes.append(route_data)

    if strategic_routes:
        # Sort by most profitable first
        df_routes = pd.DataFrame(strategic_routes)
        df_routes = df_routes.sort_values(by=['Date', 'Revenue/Hour'], ascending=[True, False])
        
        # Deduplicate - A trip cluster shouldn't be assigned to both hubs, pick the most profitable hub
        df_routes = df_routes.drop_duplicates(subset=['Date', 'Route Description'], keep='first')
        
        df_routes.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Found {len(df_routes)} ultra-profitable 4-person multi-loads! Saved to {OUTPUT_FILE}.")
    else:
        print("⚠️ No routes met the strict density (4+ trips) and profitability ($45+/hr) criteria.")
        # Create empty file so analyze_patterns doesn't crash
        pd.DataFrame(columns=["Date", "Hub", "Broker", "Job Count", "Shift Length (Hrs)", "Revenue/Hour", "Total Revenue", "Route Description", "Start Address"]).to_csv(OUTPUT_FILE, index=False)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    optimize_routes()