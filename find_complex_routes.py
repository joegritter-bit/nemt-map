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
from config import get_logger
log = get_logger(__name__)

from config import (DB_PATH, ROUTES_FILE, CLINICS_FILE, MIN_PROFIT_PER_HOUR,
                    MAX_SHIFT_HOURS, MAX_DEADHEAD_MINUTES, HUBS, CITY_COUNTY_MAP,
                    VAN_CAPACITY, AVG_MPH, MIDWEST_VIEWBOX, EXCLUDED_COUNTIES)
OUTPUT_FILE = ROUTES_FILE  # local alias

MAX_WAIT_MINUTES = 120

# --- 💰 CONTRACT DATA ---
from mtm_rates import MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT, STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE, COUNTY_BASE_RATES

# --- 🌍 GEOCODING ---
geolocator = Nominatim(user_agent="JoeNEMT_Bot_v1_complex_routes", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=2.0, max_retries=3, error_wait_seconds=4)

def get_db_connection(): return sqlite3.connect(DB_PATH, timeout=30)

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
            addr_lower = clean.lower()
            for city, c_name in CITY_COUNTY_MAP.items():
                if city in addr_lower:
                    county = c_name
                    break
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon, county) VALUES (?, ?, ?, ?)",
                           (clean, loc.latitude, loc.longitude, county))
            conn.commit()
            return loc.latitude, loc.longitude, county
    except Exception as e:
        log.warning(f"Geocoding failed for address '{clean}': {e}")
    return None, None, "Unknown"

COUNTY_PRIORITY = {
    "Sangamon County": 1.15, "Vermilion County": 1.10,
    "Macon County": 1.05, "Champaign County": 1.05
}

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
    base_result = round(one_way_price if is_modivcare else one_way_price * 2, 2)
    priority_mult = COUNTY_PRIORITY.get(county, 1.0)
    return round(base_result * priority_mult, 2)


# --- 🧠 THE HYBRID ROUTE BUILDER ---
def build_shifts(pool, hub_name, hub_coords):
    manifests = []
    
    unassigned = sorted(pool, key=lambda x: x['dt_start'])
    
    while unassigned:
        current_shift = []
        seed = unassigned.pop(0)
        current_shift.append(seed)
        
        current_time = seed['dt_end']
        current_loc = seed['coords_pu']  # after round trip, driver returns to pickup location
        
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
                # Clinic jobs allow longer scheduling window (flexible morning appointments)
                effective_max_wait = MAX_WAIT_MINUTES * 2 if candidate.get('is_clinic') else MAX_WAIT_MINUTES
                if wait_mins > effective_max_wait: continue
                
                # 🔴 FIX: Check Shift Length BEFORE Adding
                potential_end_time = candidate['dt_end']
                potential_duration = (potential_end_time - current_shift[0]['dt_start']).total_seconds() / 3600
                
                # Look ahead: Add return commute home to duration (driver ends at coords_pu after round trip)
                commute_home_hours = geodesic(candidate['coords_pu'], hub_coords).miles / AVG_MPH
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
                current_loc = best_job['coords_pu']  # driver returns to pickup after round trip
                unassigned.pop(best_idx)
            else:
                break 
        
        if len(current_shift) >= 1:
            total_rev = sum(j.get('display_revenue', j['est_revenue']) for j in current_shift)
            
            commute_start = geodesic(hub_coords, current_shift[0]['coords_pu']).miles / AVG_MPH
            commute_end = geodesic(current_shift[-1]['coords_pu'], hub_coords).miles / AVG_MPH
            
            work_hours = (current_shift[-1]['dt_end'] - current_shift[0]['dt_start']).total_seconds() / 3600
            total_hours = work_hours + commute_start + commute_end

            # Hard cap — reject shifts that exceed limit including commute
            if total_hours > MAX_SHIFT_HOURS + 0.5:  # 30 min grace for rounding
                continue

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
                
                is_clinic_shift = any(j.get('is_clinic') for j in current_shift)
                top_county = max(
                    (j.get('county', 'Unknown') for j in current_shift),
                    key=lambda c: COUNTY_BASE_RATES.get(c, 0)
                )
                manifests.append({
                    "Date": current_shift[0]['date'],
                    "Hub": hub_name,
                    "Broker": broker_label,
                    "Model": "Clinic" if is_clinic_shift else "Traditional",
                    "Shift Length (Hrs)": round(total_hours, 1),
                    "Total Revenue": round(total_rev, 2),
                    "Revenue/Hour": round(profit, 2),
                    "Job Count": job_count,
                    "Top County": top_county,
                    "Route Description": " ➡ ".join(desc_parts),
                    "Start Address": current_shift[0]['pickup_clean'],
                    "has_stale_leg": any(j.get('has_stale_leg', False) for j in current_shift),
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
    cutoff_time = pd.Timestamp.now() - pd.Timedelta(minutes=150)
    stale_threshold = cutoff_time + pd.Timedelta(minutes=30)  # danger zone: seen 120-150 min ago
    fresh_df = df[df[time_col] >= cutoff_time].copy()
    
    print(f"   📉 Active Trips: {len(fresh_df)}")
    if fresh_df.empty:
        log.error("No active trips found in DB after freshness filter. Check scraper ran successfully.")
        conn.close(); return

    fresh_df['dt_date'] = pd.to_datetime(fresh_df['date'], errors='coerce')
    fresh_df = fresh_df[fresh_df['dt_date'] >= pd.Timestamp.now().normalize()].copy()
    
    # Load full geocache into memory first
    cached_coords = pd.read_sql_query(
        "SELECT address, lat, lon FROM geo_cache WHERE lat != 0 AND lat IS NOT NULL", conn)
    local_geo = {
        row['address']: (row['lat'], row['lon'])
        for _, row in cached_coords.iterrows()
    }
    log.info(f"Loaded {len(local_geo)} cached addresses into memory")

    def fast_get_lat_lon(conn, address, local_cache):
        clean = address.replace('\n', ' ').strip()
        if clean in local_cache:
            return local_cache[clean][0], local_cache[clean][1], "Unknown"
        # Do NOT hit live API during pipeline run — skip uncached addresses
        log.info(f"Address not cached, skipping: {clean[:40]}")
        return None, None, "Unknown"

    all_routes = []

    for date, daily_trips in fresh_df.groupby('dt_date'):
        day_str = date.strftime('%Y-%m-%d')
        daily_list = daily_trips.to_dict('records')
        raw_jobs = []

        for t in daily_list:
            if 'chicago' in str(t.get('pickup_address', '')).lower():
                continue
            if 'chicago' in str(t.get('dropoff_address', '')).lower():
                continue
            lat_pu, lon_pu, county_pu = fast_get_lat_lon(conn, t['pickup_address'], local_geo)
            lat_do, lon_do, _ = fast_get_lat_lon(conn, t['dropoff_address'], local_geo)
            if county_pu in EXCLUDED_COUNTIES:
                log.warning(f"Skipping Chicago-area trip {t.get('trip_id', '?')} in {county_pu}")
                continue
            if lat_pu and lat_do:
                t.update({'coords_pu': (lat_pu, lon_pu), 'coords_do': (lat_do, lon_do)})
                try:
                    t['dt_start'] = pd.to_datetime(f"{day_str} {t['pickup_time']}")
                    dist = float(t.get('miles', 0)) if t.get('miles') else geodesic(t['coords_pu'], t['coords_do']).miles
                    t['est_revenue'] = estimate_revenue(t, county_pu)
                    payout_val = float(t.get('payout', 0)) if t.get('payout') else 0
                    if payout_val > 0:
                        # MTM payout is one-way only — double it; Modivcare payout is already round-trip
                        t['display_revenue'] = payout_val if t.get('broker') == 'Modivcare' else payout_val * 2
                    else:
                        t['display_revenue'] = t['est_revenue']
                    t['county'] = county_pu

                    drive_hrs = dist / AVG_MPH
                    is_clinic_job = any(k in t['dropoff_address'].lower() for k in clinic_keywords)
                    wait_hrs = (5 / 60) if is_clinic_job else 1.0  # 5 min clinic, 1 hr standard
                    # Full round trip: drive out + appointment wait + drive back + 15 min buffer
                    t['dt_end'] = t['dt_start'] + timedelta(hours=(drive_hrs * 2) + wait_hrs + 0.25)

                    addr_parts = t['pickup_address'].split(',')
                    t['pickup_clean'] = ",".join(addr_parts[:2]).strip()
                    t['type'] = 'Single'
                    t['sub_jobs'] = 1
                    t['is_clinic'] = is_clinic_job
                    
                    raw_jobs.append(t)
                except Exception as e:
                    log.warning(f"Skipped trip {t.get('trip_id', '?')} ({t.get('pickup_address', '?')}): {e}")
                    continue

        # CLUSTERING
        CLUSTER_BONUS = {2: 1.10, 3: 1.20, 4: 1.30}
        pool = []
        claimed_indices = set()

        destinations = {}
        for idx, t in enumerate(raw_jobs):
            dest_key = t['dropoff_address'].lower().split(',')[0]
            if dest_key not in destinations: destinations[dest_key] = []
            destinations[dest_key].append(idx)

        def _flush_batch(batch, dest, pool, claimed_indices, raw_jobs, stale_threshold, time_col):
            """Promote a completed multi-load batch to a super_job and add to pool."""
            super_job = batch[0].copy()
            bonus = CLUSTER_BONUS.get(len(batch), 1.0)
            super_job['est_revenue'] = sum(b['est_revenue'] for b in batch) * bonus
            super_job['display_revenue'] = sum(b.get('display_revenue', b['est_revenue']) for b in batch)
            super_job['dt_end'] = batch[-1]['dt_end']
            super_job['job_desc'] = f"{len(batch)}x to {dest[:10]}"
            super_job['type'] = 'BUS'
            super_job['sub_jobs'] = len(batch)
            super_job['has_stale_leg'] = any(
                pd.notna(b.get(time_col)) and b.get(time_col) < stale_threshold
                for b in batch
            )
            pool.append(super_job)
            for b in batch: claimed_indices.add(raw_jobs.index(b))

        for dest, indices in destinations.items():
            if len(indices) < 2: continue
            cluster = [raw_jobs[i] for i in indices]
            cluster.sort(key=lambda x: x['dt_start'])

            batch = [cluster[0]]
            for i in range(1, len(cluster)):
                time_diff = (cluster[i]['dt_start'] - batch[0]['dt_start']).total_seconds() / 60
                # Fix 2: per-leg freshness gate — both legs must be individually live
                leg_ts = cluster[i].get(time_col)
                leg_fresh = pd.notna(leg_ts) and leg_ts >= cutoff_time
                # Fix 4: broker guard — cross-broker trips must not be clustered
                same_broker = (str(cluster[i].get('broker', 'MTM')).strip() ==
                               str(batch[0].get('broker', 'MTM')).strip())
                if time_diff < 90 and len(batch) < VAN_CAPACITY and leg_fresh and same_broker:
                    batch.append(cluster[i])
                else:
                    if len(batch) > 1:
                        _flush_batch(batch, dest, pool, claimed_indices, raw_jobs, stale_threshold, time_col)
                    batch = [cluster[i]]

            if len(batch) > 1:
                _flush_batch(batch, dest, pool, claimed_indices, raw_jobs, stale_threshold, time_col)

        # POOLING
        for i, job in enumerate(raw_jobs):
            if i not in claimed_indices:
                t_val = job.get(time_col)
                job['has_stale_leg'] = pd.notna(t_val) and t_val < stale_threshold
                pool.append(job)

        # BUILDING
        if pool:
            print(f"   🏗️  Optimizing {day_str}...", end="\r")
            for hub_name, hub_data in HUBS.items():
                routes = build_shifts(pool.copy(), hub_name, hub_data['coords'])
                all_routes.extend(routes)

    print(f"\n✅ Analysis Complete. Found {len(all_routes)} robust shifts.")
    conn.commit()
    conn.close()
    
    # Remove any routes that still exceed shift cap or are Chicago area
    all_routes = [
        r for r in all_routes
        if float(r.get('Shift Length (Hrs)', 0)) <= MAX_SHIFT_HOURS + 0.5
        and r.get('Top County', '') not in EXCLUDED_COUNTIES
    ]

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