import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import re
import warnings

warnings.filterwarnings('ignore')


# --- CONFIGURATION ---
DB_PATH = 'data/nemt_data.db'
CLINICS_FILE = 'clinics.txt'
OUTPUT_FILE = 'profitable_routes.csv'

HUBS = {
    "Effingham": "506 South St, Effingham, IL 62401",
    "Springfield": "Springfield, IL" # Using city as address for now
}

CHICAGO_AREA_SUBURBS = [
    "chicago", "aurora", "joliet", "naperville", "rockford", "elgin", "waukegan",
    "cicero", "evanston", "bolingbrook", "schaumburg", "arlington heights",
    "skokie", "des plaines", "orland park", "tinley park", "oak lawn",
    "berwyn", "mount prospect", "wheaton", "normal", "hoffman estates",
    "downers grove", "glenview", "plainfield", "elmhurst", "lombard",
    "moline", "buffalo grove", "romeoville", "urbana", "champaign", "peoria",
    "bloomington"
]

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
geolocator = Nominatim(user_agent="JoeNEMT_Bot_v1_find_profitable_routes", timeout=10)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.1, max_retries=3, error_wait_seconds=2)


def get_db_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
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
    
    try:
        loc = geocode_service(clean, country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if not loc:
            loc = geocode_service(force_illinois_context(clean), country_codes='us', viewbox=MIDWEST_VIEWBOX)
        if loc:
            cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, ?, ?)", (clean, loc.latitude, loc.longitude))
            return loc.latitude, loc.longitude
    except: pass
    cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, 0, 0)", (clean,))
    return None, None


def load_available_trips(conn):
    """Loads available trips from the database and filters out Chicago area trips."""
    df = pd.read_sql_query("SELECT * FROM trips", conn)

    # Filter out Chicago area trips
    for suburb in CHICAGO_AREA_SUBURBS:
        df = df[~df['pickup_address'].str.contains(suburb, case=False, na=False)]
        df = df[~df['dropoff_address'].str.contains(suburb, case=False, na=False)]

    return df


def load_priority_clinics():
    """Loads priority clinics from the clinics.txt file."""
    if not os.path.exists(CLINICS_FILE):
        return []
    with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


import itertools

# ... (previous code remains the same) ...

def calculate_route_details(trips, hub_coords, conn, priority_clinics):
    """
    Calculates the total time and distance for a given route, including multi-loading.
    """
    if not trips:
        return None

    num_passengers = len(trips)
    total_distance = 0
    total_time = 0

    # For simplicity, assume the dropoff is the same for all trips in the list
    dropoff_address = trips[0]['dropoff_address']
    dropoff_coords = get_lat_lon(conn, dropoff_address)
    if not dropoff_coords:
        return None

    # --- Leg A: Hub -> Pickups -> Destination ---
    
    # Start from the hub
    current_location = hub_coords
    
    # Pickup passengers
    for trip in trips:
        pickup_coords = get_lat_lon(conn, trip['pickup_address'])
        if not pickup_coords:
            return None # Cannot calculate route if a pickup is not geocoded
        
        distance = geodesic(current_location, pickup_coords).miles
        total_distance += distance
        total_time += distance / 40 # Assume 40 mph
        current_location = pickup_coords

    # Drive to the final dropoff destination
    distance_to_dropoff = geodesic(current_location, dropoff_coords).miles
    total_distance += distance_to_dropoff
    total_time += distance_to_dropoff / 40
    
    # --- Appointment Wait Time ---
    is_priority_clinic = any(clinic in dropoff_address for clinic in priority_clinics)
    total_time += 0.08 if is_priority_clinic else 1.0 # 5 mins vs 1 hour

    # --- Leg B: Destination -> Dropoffs -> Hub ---
    current_location = dropoff_coords
    
    # Dropoff passengers (in reverse order of pickup for this simple model)
    for trip in reversed(trips):
        pickup_coords = get_lat_lon(conn, trip['pickup_address']) #This is their home address
        if not pickup_coords:
            return None
        
        distance = geodesic(current_location, pickup_coords).miles
        total_distance += distance
        total_time += distance / 40
        current_location = pickup_coords

    # Return to hub
    distance_to_hub = geodesic(current_location, hub_coords).miles
    total_distance += distance_to_hub
    total_time += distance_to_hub / 40
    
    payout = sum(trip.get('payout', 0) for trip in trips)

    return {
        "total_distance": round(total_distance, 2),
        "total_time": round(total_time, 2),
        "num_trips": len(trips),
        "total_payout": payout,
        "revenue_per_hour": round(payout / total_time, 2) if total_time > 0 else 0,
        "description": f"{num_passengers} passengers to {dropoff_address}"
    }


def find_profitable_routes():
    """
    The main function to find profitable routes.
    """
    print("Finding profitable routes...")
    conn = get_db_connection()
    available_trips = load_available_trips(conn)
    priority_clinics = load_priority_clinics()

    print(f"Loaded {len(available_trips)} trips after filtering Chicago area.")
    print(f"Loaded {len(priority_clinics)} priority clinics.")

    hub_coords = {name: get_lat_lon(conn, addr) for name, addr in HUBS.items()}
    print(f"Hub coordinates: {hub_coords}")
    
    profitable_routes = []
    
    # Group trips by destination
    grouped_by_destination = available_trips.groupby('dropoff_address')

    for destination, group in grouped_by_destination:
        trips = group.to_dict('records')
        
        # Generate combinations of trips (1 to 4 passengers)
        for i in range(1, min(len(trips), 4) + 1):
            for combo in itertools.combinations(trips, i):
                for hub_name, coords in hub_coords.items():
                    route_details = calculate_route_details(list(combo), coords, conn, priority_clinics)
                    
                    if route_details and route_details['total_time'] <= 10.0:
                        route_details['hub'] = hub_name
                        profitable_routes.append(route_details)

    # Sort routes by profitability
    profitable_routes.sort(key=lambda x: x['revenue_per_hour'], reverse=True)

    # Save to CSV
    df_profitable = pd.DataFrame(profitable_routes)
    df_profitable.to_csv(OUTPUT_FILE, index=False)
    
    print(f"Found {len(profitable_routes)} profitable routes. Saved to {OUTPUT_FILE}")
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    find_profitable_routes()
