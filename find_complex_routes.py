import pandas as pd
import sqlite3
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime, timedelta
import warnings
import os
import sys

warnings.filterwarnings('ignore')

# 🔧 SETTINGS
DB_PATH = 'data/nemt_data.db'
OUTPUT_FILE = 'potential_routes.csv'
CLINICS_FILE = 'clinics.txt'

# ✅ OPERATIONAL TARGETS
MIN_PROFIT_PER_HOUR = 32.00  
MAX_SHIFT_HOURS = 11.0       # 🔴 UPDATED: Strict 11-hour Cap
MAX_DEADHEAD_MINUTES = 60    
MAX_WAIT_MINUTES = 120       

HUBS = {
    "Effingham": {"coords": (39.1200, -88.5434)},   
    "Springfield": {"coords": (39.8017, -89.6680)}  
}

# --- 💰 CONTRACT DATA ---
MTM_MILEAGE_RATE = 1.50
MILEAGE_BAND_LIMIT = 5.0
STANDARD_BASE_RATE = 20.00
AFTER_HOURS_BASE_RATE = 20.00

COUNTY_BASE_RATES = {
    "Coles County": 40.00, "Fayette County": 40.00, "Clay County": 40.00,
    "Marion County": 50.00, "Jefferson County": 50.00,
    "Christian County": 35.00, "Macon County": 35.00, "Piatt County": 35.00, "Champaign County": 35.00,
    "Sangamon County": 65.00, "Vermilion County": 65.00, "Edgar County": 40.00, "Clark County": 40.00
}

# 🔴 ADDED: Backup Lookup for when Geocoder Fails
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

# --- ⏳ LOGISTICS ---
VAN_CAPACITY = 4       
AVG_MPH = 50.0 

# --- 🌍 GEOCODING ---
geolocator = Nominatim(user_agent="jgritter_nemt_v11_3", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.0)
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

def get_db_connection(): return sqlite3.connect(DB_PATH)

def load_clinic_keywords():
    if not os.path.exists(CLINICS_FILE): return []
    with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip()]

def get_lat_lon(conn, address):
    if not isinstance(address, str): return None, None, "Unknown"
    clean = address.replace('\n', ' ').strip()
    cursor = conn.cursor()
    cursor.execute("SELECT lat, lon, county FROM geo_cache WHERE address = ?", (clean,))
    res = cursor.fetchone()
    if res and res[0] != 0: 
        return res[0], res[1], res[2]
    try:
        loc = geocode_service(clean + ", Illinois", country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if loc:
            county = "Unknown" 
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon, county) VALUES (?, ?, ?, ?)", 
                           (clean, loc.latitude, loc.longitude, county))
            conn.commit()
            return loc.latitude, loc.longitude, county
    except: pass
    return None, None, "Unknown"

def estimate_revenue(row, county):
    """ Calculates estimated revenue (2x MTM Multiplier). """
    is_modivcare = row.get('broker') == 'Modivcare'
    actual = float(row.get('payout', 0)) if row.get('payout') else 0
    if actual > 0:
        return actual if is_modivcare else actual * 2
    
    # 🔴 FIX: Check Manual Map if County is Unknown or Low Value
    if county == "Unknown" or county not in COUNTY_BASE_RATES:
        addr_lower = row.get('pickup_address', '').lower()
        for city, c_name in CITY_COUNTY_MAP.items():
            if city in addr_lower:
                county = c_name
                break

    pickup_time = pd.to_datetime(row['dt_start'])
    base_rate = COUNTY_BASE_RATES.get(county, STANDARD_BASE_RATE)
    
    if pickup_time.hour < 6 or pickup_time.hour >= 18: 
        base_rate = max(base_rate, AFTER_HOURS_BASE_RATE)
        
    miles = float(row.get('miles', 0)) if row.get('miles') else 0
    if miles == 0 and row.get('coords_pu') and row.get('coords_do'):
        miles = geodesic(row['coords_pu'], row['coords_do']).miles * 1.3
        
    billable_miles = max(0, miles - MILEAGE_BAND_LIMIT)
    one_way_price = base_rate + (billable_miles * MTM_MILEAGE_RATE)
    return round(one_way_price if is_modivcare else one_way_price * 2, 2)

# --- 🧠 THE HYBRID ROUTE BUILDER ---
def build_shifts(pool, hub_name, hub_coords):
    manifests = []
    
    unassigned = sorted(pool, key=lambda x: x['dt_start'])
    
    while unassigned:
        current_shift = []
        seed = unassigned.pop(0)
        current_shift.append(seed)
        
        current_time = seed['dt_end']
        current_loc = seed['coords_do'] 
        
        while True:
            best_job = None
            best_score = -999
            best_idx = -1
            
            for i, candidate in enumerate(unassigned):
                drive_miles = geodesic(current_loc, candidate['coords_pu']).miles
                drive_mins = (drive_miles / AVG_MPH) * 60
                
                arrival_time = current_time + timedelta(minutes=drive_mins)
                wait_mins = (candidate['dt_start'] - arrival_time).total_seconds() / 60
                
                if wait_mins < -15: continue 
                if drive_mins > MAX_DEADHEAD_MINUTES: continue 
                if wait_mins > MAX_WAIT_MINUTES: continue 
                
                # 🔴 FIX: Check Shift Length BEFORE Adding
                potential_end_time = candidate['dt_end']
                potential_duration = (potential_end_time - current_shift[0]['dt_start']).total_seconds() / 3600
                
                # Look ahead: Add return commute home to duration
                commute_home_hours = geodesic(candidate['coords_do'], hub_coords).miles / AVG_MPH
                total_projected_hours = potential_duration + commute_home_hours

                if total_projected_hours > MAX_SHIFT_HOURS: continue

                score = candidate['est_revenue'] - (drive_miles * 0.50) - (wait_mins * 0.25)
                
                if score > best_score:
                    best_score = score
                    best_job = candidate
                    best_idx = i
            
            if best_job:
                current_shift.append(best_job)
                current_time = best_job['dt_end']
                current_loc = best_job['coords_do']
                unassigned.pop(best_idx)
            else:
                break 
        
        if len(current_shift) >= 1: 
            total_rev = sum(j['est_revenue'] for j in current_shift)
            
            commute_start = geodesic(hub_coords, current_shift[0]['coords_pu']).miles / AVG_MPH
            commute_end = geodesic(current_shift[-1]['coords_do'], hub_coords).miles / AVG_MPH
            
            work_hours = (current_shift[-1]['dt_end'] - current_shift[0]['dt_start']).total_seconds() / 3600
            total_hours = work_hours + commute_start + commute_end
            
            profit = total_rev / total_hours if total_hours > 0 else 0
            
            if profit >= MIN_PROFIT_PER_HOUR or len(current_shift) >= 4:
                brokers = set(j.get('broker', 'MTM') for j in current_shift)
                brokers = {b for b in brokers if b and str(b).lower() != 'nan'}
                
                if len(brokers) == 1: broker_label = list(brokers)[0]
                elif len(brokers) == 0: broker_label = "MTM"
                else: broker_label = "Mixed"

                job_count = sum(j.get('sub_jobs', 1) for j in current_shift)

                desc_parts = []
                for j in current_shift:
                    time_str = j['pickup_time']
                    addr_short = j['pickup_clean'].split(',')[0][:15]
                    if "BUS" in j.get('type', ''): desc_parts.append(f"🚌 {j['job_desc']}")
                    else: desc_parts.append(f"{time_str} ({addr_short})")
                
                manifests.append({
                    "Date": current_shift[0]['date'],
                    "Hub": hub_name,
                    "Broker": broker_label,
                    "Shift Length (Hrs)": round(total_hours, 1),
                    "Total Revenue": round(total_rev, 2),
                    "Revenue/Hour": round(profit, 2),
                    "Job Count": job_count,
                    "Route Description": " ➡ ".join(desc_parts),
                    "Start Address": current_shift[0]['pickup_clean']
                })
                
    return manifests

def find_complex_routes():
    print(f"🚀 Running Analysis v11.3 (Strict 11h Cap)...")
    if os.path.exists(OUTPUT_FILE): os.remove(OUTPUT_FILE)

    conn = get_db_connection()
    conn.execute("CREATE TABLE IF NOT EXISTS geo_cache (address TEXT PRIMARY KEY, lat REAL, lon REAL, county TEXT)")
    
    clinic_keywords = load_clinic_keywords()
    
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    
    time_col = 'last_seen' if 'last_seen' in df.columns else 'timestamp'
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    latest_scan = df[time_col].max()
    cutoff_time = latest_scan - pd.Timedelta(minutes=120) 
    fresh_df = df[df[time_col] >= cutoff_time].copy()
    
    print(f"   📉 Active Trips: {len(fresh_df)}")
    
    fresh_df['dt_date'] = pd.to_datetime(fresh_df['date'], errors='coerce')
    fresh_df = fresh_df[fresh_df['dt_date'] >= pd.Timestamp.now().normalize()].copy()
    
    all_routes = []
    
    for date, daily_trips in fresh_df.groupby('dt_date'):
        day_str = date.strftime('%Y-%m-%d')
        daily_list = daily_trips.to_dict('records')
        raw_jobs = []

        for t in daily_list:
            lat_pu, lon_pu, county_pu = get_lat_lon(conn, t['pickup_address'])
            lat_do, lon_do, _ = get_lat_lon(conn, t['dropoff_address'])
            if lat_pu and lat_do:
                t.update({'coords_pu': (lat_pu, lon_pu), 'coords_do': (lat_do, lon_do)})
                try:
                    t['dt_start'] = pd.to_datetime(f"{day_str} {t['pickup_time']}")
                    dist = float(t.get('miles', 0)) if t.get('miles') else geodesic(t['coords_pu'], t['coords_do']).miles
                    t['est_revenue'] = estimate_revenue(t, county_pu)
                    
                    drive_hrs = (dist / AVG_MPH)
                    t['dt_end'] = t['dt_start'] + timedelta(hours=(drive_hrs * 2) + 0.50)
                    
                    addr_parts = t['pickup_address'].split(',')
                    t['pickup_clean'] = ",".join(addr_parts[:2]).strip()
                    t['type'] = 'Single'
                    t['sub_jobs'] = 1
                    t['is_clinic'] = any(k in t['dropoff_address'].lower() for k in clinic_keywords)
                    
                    raw_jobs.append(t)
                except: continue

        # CLUSTERING
        pool = []
        claimed_indices = set()
        
        destinations = {}
        for idx, t in enumerate(raw_jobs):
            dest_key = t['dropoff_address'].lower().split(',')[0]
            if dest_key not in destinations: destinations[dest_key] = []
            destinations[dest_key].append(idx)
            
        for dest, indices in destinations.items():
            if len(indices) < 2: continue
            cluster = [raw_jobs[i] for i in indices]
            cluster.sort(key=lambda x: x['dt_start'])
            
            batch = [cluster[0]]
            for i in range(1, len(cluster)):
                time_diff = (cluster[i]['dt_start'] - batch[0]['dt_start']).total_seconds() / 60
                if time_diff < 90 and len(batch) < VAN_CAPACITY:
                    batch.append(cluster[i])
                else:
                    if len(batch) > 1:
                        super_job = batch[0].copy()
                        super_job['est_revenue'] = sum(b['est_revenue'] for b in batch)
                        super_job['dt_end'] = batch[-1]['dt_end'] 
                        super_job['job_desc'] = f"{len(batch)}x to {dest[:10]}"
                        super_job['type'] = 'BUS'
                        super_job['sub_jobs'] = len(batch)
                        pool.append(super_job)
                        for b in batch: claimed_indices.add(raw_jobs.index(b))
                    batch = [cluster[i]]
            
            if len(batch) > 1:
                super_job = batch[0].copy()
                super_job['est_revenue'] = sum(b['est_revenue'] for b in batch)
                super_job['dt_end'] = batch[-1]['dt_end']
                super_job['job_desc'] = f"{len(batch)}x to {dest[:10]}"
                super_job['type'] = 'BUS'
                super_job['sub_jobs'] = len(batch)
                pool.append(super_job)
                for b in batch: claimed_indices.add(raw_jobs.index(b))

        # POOLING
        for i, job in enumerate(raw_jobs):
            if i not in claimed_indices:
                pool.append(job)

        # BUILDING
        if pool:
            print(f"   🏗️  Optimizing {day_str}...", end="\r")
            for hub_name, hub_data in HUBS.items():
                routes = build_shifts(pool.copy(), hub_name, hub_data['coords'])
                all_routes.extend(routes)

    print(f"\n✅ Analysis Complete. Found {len(all_routes)} robust shifts.")
    conn.close()
    
    if all_routes:
        res = pd.DataFrame(all_routes)
        res['Date_Obj'] = pd.to_datetime(res['Date'])
        res = res.sort_values(by=['Date_Obj', 'Revenue/Hour'], ascending=[True, False])
        res = res.drop(columns=['Date_Obj'])
        
        res = res.drop_duplicates(subset=['Date', 'Route Description'], keep='first')
        res.to_csv(OUTPUT_FILE, index=False)
        print(f"📄 Saved to {OUTPUT_FILE}")
    else:
        print("⚠️ No routes found.")

if __name__ == "__main__": find_complex_routes()