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

# 🔧 SETTINGS
DRIVER_FILE = 'driver_schedule.csv'
DB_PATH = 'data/nemt_data.db'
DEPOT_ADDRESS = "506 South St, Effingham, IL 62401"

# CONSTRAINTS
MAX_SHIFT_HOURS = 10.0  # Max workday length (Keys in to Keys out)
MAX_RADIUS_MILES = 30   # How far to chase a trip
AVG_MPH = 40            # Average speed for estimations
MIN_GAP_HOURS = 0.5     # Minimum break to fill

# 🌍 GEOCODING ENGINE
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

# ✅ FIXED: New User Agent to bypass 403 Error
geolocator = Nominatim(user_agent="jgritter_nemt_stitcher_v92", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

def get_db_connection():
    return sqlite3.connect(DB_PATH)

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
    
    # Try fuzzy match if exact fails
    cursor.execute("SELECT lat, lon FROM geo_cache WHERE address LIKE ?", (f"{clean[:15]}%",))
    res = cursor.fetchone()
    if res and res[0] != 0: return res
    
    # Active Learning
    print(f"      🌍 Learning location: {clean[:35]}...")
    try:
        loc = geocode_service(clean, country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if not loc:
            loc = geocode_service(force_illinois_context(clean), country_codes='us', viewbox=MIDWEST_VIEWBOX)
        
        if loc:
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, ?, ?)", 
                           (clean, loc.latitude, loc.longitude))
            conn.commit()
            return loc.latitude, loc.longitude
    except: pass
    
    # Save failure to prevent re-querying
    cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, 0, 0)", (clean,))
    conn.commit()
    return None, None

def safe_get_price(row):
    try:
        val = row.get('payout', 0)
        if pd.isna(val) or val == 'None' or val == '':
            return 0.0, "Check Price"
        return float(val), f"${float(val):.2f}"
    except:
        return 0.0, "Check Price"

def analyze_driver_schedule():
    # Only run if the schedule file actually exists
    if not os.path.exists(DRIVER_FILE):
        print(f"⚠️  Skipping Stitcher: '{DRIVER_FILE}' not found.")
        return []

    print("🧵 Running Schedule Stitcher (Freshness Mode)...")
    conn = get_db_connection()
    depot_coords = get_lat_lon(conn, DEPOT_ADDRESS)
    
    try:
        driver_df = pd.read_csv(DRIVER_FILE)
        driver_df.columns = driver_df.columns.str.strip()
    except Exception as e:
        print(f"❌ Error reading Schedule CSV: {e}")
        conn.close()
        return []

    # Load Market Data
    market_df = pd.read_sql_query("SELECT * FROM trips", conn)
    market_df['dt_date'] = pd.to_datetime(market_df['date'], errors='coerce')
    today = pd.Timestamp.now().normalize()
    
    # --- 🛡️ FRESHNESS FILTER 🛡️ ---
    if 'last_seen' in market_df.columns:
        market_df['last_seen'] = pd.to_datetime(market_df['last_seen'], errors='coerce')
        
        # Determine the moment of the most recent scan
        last_run = market_df['last_seen'].max()
        cutoff = last_run - timedelta(minutes=45)
        
        # Keep ONLY trips seen in the last 45 mins + Future Dates
        market_df = market_df[
            (market_df['dt_date'] >= today) & 
            (market_df['last_seen'] >= cutoff)
        ]
    else:
        market_df = market_df[market_df['dt_date'] >= today]

    if market_df.empty:
        print("   ⚠️ No active future trips found (Check scraper logs!).")
        conn.close()
        return []
    
    print(f"   🔎 Scanning {len(market_df)} active trips against driver schedule...")

    driver_df['dt_date'] = pd.to_datetime(driver_df['Date'], errors='coerce')
    opportunities = []

    # --- 🔄 THE LOOP: Checks EVERY date in the CSV ---
    for date, group in driver_df.groupby('dt_date'):
        day_name = date.day_name()
        date_str = date.strftime('%m/%d')
        
        # print(f"      🗓️ Checking schedule for: {day_name} {date_str}...")

        try:
            group['sort_ts'] = pd.to_datetime(group['Date'] + ' ' + group['Scheduled PU'])
            group = group.sort_values('sort_ts')
            trips = group.to_dict('records')
            
            # --- SHIFT SETUP ---
            first_trip = trips[0]
            start_coords = get_lat_lon(conn, first_trip['PU Address'])
            if not start_coords or not start_coords[0]: continue
            
            commute_hours = geodesic(depot_coords, start_coords).miles / AVG_MPH
            t_first_pickup = pd.to_datetime(f"{date.date()} {first_trip['Scheduled PU']}")
            t_shift_start = t_first_pickup - timedelta(hours=commute_hours)
            t_hard_stop = t_shift_start + timedelta(hours=MAX_SHIFT_HOURS)
            
            daily_candidates = market_df[market_df['dt_date'].dt.date == date.date()].copy()
            if daily_candidates.empty: continue

            # PART 1: GAPS
            for i in range(len(trips) - 1):
                trip_a = trips[i]
                trip_b = trips[i+1]
                
                t_pu_a = pd.to_datetime(f"{date.date()} {trip_a['Scheduled PU']}")
                drive_a = (float(trip_a['Mileage']) / AVG_MPH) + 0.25
                t_free = t_pu_a + timedelta(hours=drive_a)
                t_must_return = pd.to_datetime(f"{date.date()} {trip_b['Scheduled PU']}")
                
                gap_hours = (t_must_return - t_free).total_seconds() / 3600
                if gap_hours < MIN_GAP_HOURS: continue
                
                wait_loc = trip_a['DO Address']
                coord_wait = get_lat_lon(conn, wait_loc)
                if not coord_wait or not coord_wait[0]: continue

                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(opp['date'] + ' ' + opp['pickup_time'])
                        sim_start = t_free.replace(hour=opp_ts.hour, minute=opp_ts.minute)
                        
                        if sim_start < (t_free + timedelta(minutes=15)): continue
                        
                        opp_pu = get_lat_lon(conn, opp['pickup_address'])
                        if not opp_pu or not opp_pu[0]: continue
                        
                        dist_to = geodesic(coord_wait, opp_pu).miles
                        if dist_to > MAX_RADIUS_MILES: continue
                        
                        opp_do = get_lat_lon(conn, opp['dropoff_address'])
                        if not opp_do or not opp_do[0]: continue
                        
                        job_miles = geodesic(opp_pu, opp_do).miles
                        dist_back = geodesic(opp_do, coord_wait).miles
                        loop_hours = ((dist_to + job_miles + dist_back) / AVG_MPH) + 0.25
                        
                        t_back = sim_start + timedelta(hours=loop_hours)
                        
                        if t_back < (t_must_return - timedelta(minutes=15)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": "🪃 GAP FILLER",
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}",
                                "Window": f"{t_free.strftime('%H:%M')}-{t_must_return.strftime('%H:%M')}",
                                "Trip Time": opp['pickup_time'],
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡ {opp['dropoff_address'].split(',')[0]}",
                                "Trip ID": opp.get('trip_id', 'N/A'), # ✅ ADDED
                                "Price": display_price,
                                "SortValue": sort_val
                            })
                    except: continue

            # PART 2: EXTENSIONS
            last_trip = trips[-1]
            t_last_pu = pd.to_datetime(f"{date.date()} {last_trip['Scheduled PU']}")
            drive_hrs_last = (float(last_trip['Mileage']) / AVG_MPH) + 0.25
            t_free = t_last_pu + timedelta(hours=drive_hrs_last)
            finish_loc = last_trip['DO Address']
            coord_finish = get_lat_lon(conn, finish_loc)
            
            if t_free < t_hard_stop and coord_finish and coord_finish[0]:
                for _, opp in daily_candidates.iterrows():
                    try:
                        opp_ts = pd.to_datetime(opp['date'] + ' ' + opp['pickup_time'])
                        sim_start = t_free.replace(hour=opp_ts.hour, minute=opp_ts.minute)
                        
                        if sim_start < (t_free + timedelta(minutes=15)): continue
                        if sim_start > (t_hard_stop - timedelta(hours=1)): continue
                        
                        opp_pu = get_lat_lon(conn, opp['pickup_address'])
                        if not opp_pu or not opp_pu[0]: continue
                        
                        if geodesic(coord_finish, opp_pu).miles > MAX_RADIUS_MILES: continue
                        
                        opp_do = get_lat_lon(conn, opp['dropoff_address'])
                        if not opp_do or not opp_do[0]: continue
                        
                        job_time = (geodesic(opp_pu, opp_do).miles / AVG_MPH) + 0.25
                        home_time = geodesic(opp_do, depot_coords).miles / AVG_MPH
                        
                        t_keys_out = sim_start + timedelta(hours=job_time + home_time)
                        
                        if t_keys_out <= (t_hard_stop + timedelta(minutes=45)):
                            sort_val, display_price = safe_get_price(opp)
                            opportunities.append({
                                "Type": "➕ EXTENSION",
                                "Broker": opp.get('broker', 'MTM'),
                                "Day": f"{day_name} {date_str}",
                                "Window": f"After {t_free.strftime('%H:%M')}",
                                "Trip Time": opp['pickup_time'],
                                "Route": f"{opp['pickup_address'].split(',')[0]} ➡ {opp['dropoff_address'].split(',')[0]}",
                                "Trip ID": opp.get('trip_id', 'N/A'), # ✅ ADDED
                                "Price": display_price,
                                "SortValue": sort_val
                            })
                    except: continue

        except Exception as e:
            continue

    conn.close()
    
    # Save CSV Backup AND Print Table if running manually
    if opportunities:
        df_out = pd.DataFrame(opportunities)
        df_out = df_out.sort_values('SortValue', ascending=False)
        df_out.to_csv("brandy_overtime.csv", index=False)
        
        if __name__ == "__main__":
             print(f"\n🚀 FOUND {len(opportunities)} ACTIVE OPPORTUNITIES!\n")
             cols = ["Type", "Broker", "Trip ID", "Day", "Price", "Route"]
             print(df_out[cols].to_string(index=False))
        
    return opportunities

if __name__ == "__main__":
    analyze_driver_schedule()