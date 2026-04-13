import pandas as pd
import sqlite3
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime, timedelta
import warnings
import re
import os
import logging

# Silence Geopy's noisy error logs
logging.getLogger("geopy").setLevel(logging.CRITICAL)
warnings.filterwarnings('ignore')

# 🛠 SETTINGS
DRIVER_FILE = 'driver_schedule.csv'
from config import get_logger
log = get_logger(__name__)

from config import (DB_PATH, DEPOT_ADDRESS, CLINICS_FILE, MAX_SHIFT_HOURS,
                    MAX_RADIUS_MILES, AVG_MPH, MIN_GAP_HOURS, MIDWEST_VIEWBOX,
                    CITY_COUNTY_MAP)

# 💰 PRICING DATA
from mtm_rates import MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT, STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE, COUNTY_BASE_RATES

# 🌍 GEOCODING ENGINE
# Updated User-Agent to avoid generic blocks
geolocator = Nominatim(user_agent="JoeNEMT_Bot_v1_stitch_route", timeout=15)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=2.0, max_retries=3, error_wait_seconds=4)

def get_db_connection():
    if os.path.exists(DB_PATH): return sqlite3.connect(DB_PATH, timeout=30)
    return sqlite3.connect('trips.db', timeout=30)

def load_clinics():
    """Load the clinics.txt file to identify flexible 5-minute wait times."""
    if not os.path.exists(CLINICS_FILE): return []
    try:
        with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except Exception as e:
        log.warning(f"Failed to load clinics file '{CLINICS_FILE}': {e}")
        return []

def get_wait_time_hours(dropoff_addr, clinics):
    """Returns 5 mins (0.083 hrs) for clinics, 1 hr for standard medical."""
    if not dropoff_addr: return 1.0
    clean_addr = str(dropoff_addr).lower()
    if any(c in clean_addr for c in clinics):
        return 5.0 / 60.0  # 5 minutes
    return 1.0  # 1 hour standard

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
    except Exception as e:
        log.warning(f"Geocoding failed for address '{clean}': {e}")
    try:
        cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, 0, 0)", (clean,))
        conn.commit()
    except Exception as e:
        log.warning(f"Failed to cache null geocode for '{clean}': {e}")
    return None, None

def calculate_manual_price(row):
    if row.get('broker') == 'Modivcare':
        try: return float(row.get('payout', 0))
        except Exception as e:
            log.warning(f"Modivcare payout parse failed for trip {row.get('trip_id', '?')}: {e}")
            return 0.0
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
    except Exception as e:
        log.warning(f"Price calculation failed for trip {row.get('trip_id', '?')}: {e}")
        return 0.0

def safe_get_price(row):
    price = calculate_manual_price(row)
    if price == 0:
        try:
            val = float(row.get('payout', 0))
            if val > 0: return val * 2, f"${val*2:.2f}"
        except Exception as e:
            log.warning(f"Payout fallback parse failed for trip {row.get('trip_id', '?')}: {e}")
        return 0.0, "Check Price"
    return price, f"${price:.2f}"

def analyze_driver_schedule():
    if not os.path.exists(DRIVER_FILE): return []
    print("🧵 Running Multi-Driver Stitcher v12.4 (Phase 2: Clinic Flex & Round Trips)...")
    conn = get_db_connection()
    depot_coords = get_lat_lon(conn, DEPOT_ADDRESS)
    clinics_list = load_clinics()
    
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
            except Exception as e:
                log.warning(f"Driver schedule template parse failed for row {dict(row) if hasattr(row, 'to_dict') else row}: {e}")
                continue
        for driver in templates:
            for d in templates[driver]:
                templates[driver][d].sort(key=lambda x: pd.to_datetime(x['pu_time_str']).time())
    except Exception as e:
        log.error(f"Failed to load driver schedule from '{DRIVER_FILE}': {e}")
        conn.close(); return []

    # --- 🟢 HOURLY SYNC PROTECTION: Kills Ghost Trips ---
    market_df = pd.read_sql_query("SELECT * FROM trips", conn)
    time_col = 'last_seen' if 'last_seen' in market_df.columns else 'timestamp'
    market_df[time_col] = pd.to_datetime(market_df[time_col], errors='coerce')
    
    cutoff_time = datetime.now() - timedelta(minutes=150)
    market_df = market_df[market_df[time_col] >= cutoff_time]

    market_df['dt_date'] = pd.to_datetime(market_df['date'], errors='coerce').dt.date
    today = datetime.now().date()
    market_df = market_df[market_df['dt_date'] >= today]

    if market_df.empty: 
        print("⚠️ Marketplace Snapshot is empty. No fresh trips found.")
        conn.close(); return []
        
    unique_dates = sorted(market_df['dt_date'].unique())
    opportunities = []

    # Pre-geocode all market trip addresses once before the nested loop so
    # the inner loops only do fast dict lookups instead of live API calls.
    print("   🌍 Pre-geocoding market trips...")
    geo_cache_local = {}
    all_addrs = pd.concat([market_df['pickup_address'], market_df['dropoff_address']]).dropna().unique()

    # Load already-cached addresses directly from DB (no API call)
    cached = pd.read_sql_query(
        "SELECT address, lat, lon FROM geo_cache WHERE lat != 0", conn)
    for _, row in cached.iterrows():
        geo_cache_local[row['address']] = (row['lat'], row['lon'])

    missing = [a for a in all_addrs if a not in geo_cache_local]
    log.info(f"{len(missing)} addresses not in cache — skipping "
             f"(will be cached by warm_geocache.py)")
    # Do NOT geocode live during pipeline run
    print(f"   ✅ Loaded {len(geo_cache_local)} cached addresses ({len(missing)} skipped).")

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

            # --- PART 0: PRE-SHIFT (Round Trip Logic) ---
            first_trip = todays_schedule[0]
            if first_trip['pu_coords'] and first_trip['pu_coords'][0]:
                must_arrive_by = first_trip['pu_dt'] - timedelta(minutes=15)
                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(str(opp['date']) + ' ' + opp['pickup_time'])
                        if opp_ts >= first_trip['pu_dt']: continue
                        opp_pu = geo_cache_local.get(opp['pickup_address'])
                        if not opp_pu or not opp_pu[0]: continue
                        opp_do = geo_cache_local.get(opp['dropoff_address'])
                        if not opp_do or not opp_do[0]: continue

                        drive_to_opp = geodesic(depot_coords, opp_pu).miles / AVG_MPH
                        earliest_start = pd.Timestamp(f"{current_date} 05:00:00")
                        if opp_ts < (earliest_start + timedelta(hours=drive_to_opp)): continue
                        
                        # Time Windows & Clinic Flex
                        wait_hrs = get_wait_time_hours(opp['dropoff_address'], clinics_list)
                        leg_a_hrs = geodesic(opp_pu, opp_do).miles / AVG_MPH
                        
                        # Full Round Trip Time: Leg A + Wait + Leg B (Return) + Drive to First Trip
                        drive_to_first = geodesic(opp_pu, first_trip['pu_coords']).miles / AVG_MPH
                        finish_time = opp_ts + timedelta(hours=leg_a_hrs + wait_hrs + leg_a_hrs + drive_to_first + 0.25)
                        
                        if finish_time <= must_arrive_by:
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": f"🌅 PRE-SHIFT RT ({driver})",
                                "Driver": driver,
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}",
                                "Window": f"Before {first_trip['pu_dt'].strftime('%H:%M')}",
                                "Trip Time": opp['pickup_time'],
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡️ {opp['dropoff_address'].split(',')[0]} 🔄",
                                "Trip ID": opp.get('trip_id', 'N/A'),
                                "Price": display_price, "SortValue": sort_val
                            })
                    except Exception as e:
                        log.warning(f"Pre-shift opportunity check failed for driver {driver}, trip {opp.get('trip_id', '?')}: {e}")
                        continue

            # --- PART 1: GAPS (Round Trip Logic) ---
            for i in range(len(todays_schedule) - 1):
                trip_a, trip_b = todays_schedule[i], todays_schedule[i+1]
                t_free = trip_a['pu_dt'] + timedelta(hours=(trip_a['mileage'] / AVG_MPH) + 0.25)
                if (trip_b['pu_dt'] - t_free).total_seconds() / 3600 < MIN_GAP_HOURS: continue
                if not trip_a['do_coords'] or not trip_a['do_coords'][0]: continue
                if not trip_b['pu_coords'] or not trip_b['pu_coords'][0]: continue

                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(str(opp['date']) + ' ' + opp['pickup_time'])
                        sim_start = t_free.replace(hour=opp_ts.hour, minute=opp_ts.minute)
                        if sim_start < (t_free + timedelta(minutes=15)): continue
                        opp_pu = geo_cache_local.get(opp['pickup_address'])
                        if not opp_pu or not opp_pu[0] or geodesic(trip_a['do_coords'], opp_pu).miles > MAX_RADIUS_MILES: continue
                        opp_do = geo_cache_local.get(opp['dropoff_address'])
                        
                        # Time Windows & Clinic Flex
                        wait_hrs = get_wait_time_hours(opp['dropoff_address'], clinics_list)
                        leg_a_hrs = geodesic(opp_pu, opp_do).miles / AVG_MPH
                        
                        # Full Round Trip Time: Drive to Opp + Leg A + Wait + Leg B + Drive to Trip B PU
                        drive_to_opp = geodesic(trip_a['do_coords'], opp_pu).miles / AVG_MPH
                        drive_to_b = geodesic(opp_pu, trip_b['pu_coords']).miles / AVG_MPH
                        
                        loop_hours = drive_to_opp + leg_a_hrs + wait_hrs + leg_a_hrs + drive_to_b + 0.25
                        if sim_start + timedelta(hours=loop_hours) < (trip_b['pu_dt'] - timedelta(minutes=15)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": f"🧩 GAP RT ({driver})",
                                "Driver": driver,
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}",
                                "Window": f"{t_free.strftime('%H:%M')}-{trip_b['pu_dt'].strftime('%H:%M')}",
                                "Trip Time": opp['pickup_time'],
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡️ {opp['dropoff_address'].split(',')[0]} 🔄",
                                "Trip ID": opp.get('trip_id', 'N/A'),
                                "Price": display_price, "SortValue": sort_val
                            })
                    except Exception as e:
                        log.warning(f"Gap opportunity check failed for driver {driver}, trip {opp.get('trip_id', '?')}: {e}")
                        continue

            # --- PART 2: EXTENSIONS (Round Trip Logic) ---
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
                        
                        opp_pu = geo_cache_local.get(opp['pickup_address'])
                        if not opp_pu or not opp_pu[0] or geodesic(last_trip['do_coords'], opp_pu).miles > MAX_RADIUS_MILES: continue
                        opp_do = geo_cache_local.get(opp['dropoff_address'])
                        
                        # Time Windows & Clinic Flex
                        wait_hrs = get_wait_time_hours(opp['dropoff_address'], clinics_list)
                        leg_a_hrs = geodesic(opp_pu, opp_do).miles / AVG_MPH
                        
                        # Full Round Trip Time: Drive to Opp + Leg A + Wait + Leg B + Drive to Depot
                        drive_to_opp = geodesic(last_trip['do_coords'], opp_pu).miles / AVG_MPH
                        drive_home = geodesic(opp_pu, depot_coords).miles / AVG_MPH
                        
                        t_keys_out = sim_start + timedelta(hours=drive_to_opp + leg_a_hrs + wait_hrs + leg_a_hrs + drive_home + 0.25)
                        
                        if t_keys_out <= (hard_stop + timedelta(minutes=45)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": f"➕ EXTENSION RT ({driver})",
                                "Driver": driver,
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}",
                                "Window": f"After {t_free.strftime('%H:%M')}",
                                "Trip Time": opp['pickup_time'],
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡️ {opp['dropoff_address'].split(',')[0]} 🔄",
                                "Trip ID": opp.get('trip_id', 'N/A'),
                                "Price": display_price, "SortValue": sort_val
                            })
                    except Exception as e:
                        log.warning(f"Extension opportunity check failed for driver {driver}, trip {opp.get('trip_id', '?')}: {e}")
                        continue

    conn.commit()
    conn.close()
    if opportunities:
        pd.DataFrame(opportunities).sort_values(['Day', 'SortValue'], ascending=[True, False]).to_csv("brandy_overtime.csv", index=False)
    return opportunities

if __name__ == "__main__": analyze_driver_schedule()