import sqlite3
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import re

# 🔧 SETTINGS
DB_PATH = 'data/nemt_data.db'
MAP_OUTPUT = 'nemt_war_room.html'
CLINICS_FILE = 'clinics.txt'

# Initialize Geocoder
geolocator = Nominatim(user_agent="jgritter_nemt_map_v2", timeout=15)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

# 📦 THE MIDWEST CAGE
# Defined GPS corners for [IL, MO, IN, WI, KY]
MIDWEST_VIEWBOX = [
    (35.0, -95.0), # South-West Corner
    (44.0, -84.0)  # North-East Corner
]

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def load_priority_keywords():
    if not os.path.exists(CLINICS_FILE): return []
    with open(CLINICS_FILE, 'r') as f:
        return [line.strip().lower() for line in f if line.strip()]

def ensure_cache_table(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS geo_cache (address TEXT PRIMARY KEY, lat REAL, lon REAL)')
    conn.commit()

def force_illinois_context(addr):
    """Ensures 'IL' is present in the search string."""
    if not addr: return ""
    if re.search(r'\bIL\b|\bIllinois\b', addr, re.IGNORECASE):
        return addr
    zip_match = re.search(r'(\d{5})$', addr)
    if zip_match:
        return addr[:zip_match.start()] + " IL " + addr[zip_match.start():]
    return f"{addr}, Illinois"

def clean_address_severe(addr):
    if not addr: return ""
    addr = re.split(r' Apt | Unit | Ste | Lot | Bldg | Rm | #', addr, flags=re.IGNORECASE)[0]
    addr = re.sub(r'(\d{5})-\d{4}', r'\1', addr)
    addr = re.sub(r'PO BOX \d+', '', addr, flags=re.IGNORECASE)
    addr = addr.replace(', ,', ',').strip(', ')
    return addr.strip()

def get_coordinates(conn, original_addr):
    cursor = conn.cursor()
    
    # 1. Check Cache
    clean_key = original_addr.replace('\n', ' ').strip()
    cursor.execute("SELECT lat, lon FROM geo_cache WHERE address = ?", (clean_key,))
    cached = cursor.fetchone()
    if cached and cached[0] != 0: return cached[0], cached[1]

    # 2. Prepare Strategies
    base_clean = clean_address_severe(clean_key)
    strategies = []
    
    # Strategy A: Strict
    strategies.append(force_illinois_context(base_clean))
    
    # Strategy B: Fallback (City/Zip)
    parts = base_clean.split(',')
    if len(parts) >= 2:
        strategies.append(force_illinois_context(",".join(parts[-2:]).strip()))
    else:
        words = base_clean.split()
        if len(words) >= 2 and words[-1].isdigit():
            city_zip = f"{words[-2]} {words[-1]}"
            strategies.append(force_illinois_context(city_zip))

    # EXECUTE with IRON DOME settings
    for search_query in strategies:
        try:
            print(f"   🔍 Trying: {search_query[:45]}...")
            
            # 🔒 LOCKED DOWN SEARCH
            location = geocode_service(
                search_query, 
                country_codes='us',     
                viewbox=MIDWEST_VIEWBOX,
                bounded=True  # FORCE results to stay inside the Midwest Cage
            )
            
            if location:
                # 🛑 SANITY CHECK: IL Border Logic 🛑
                # If the address says 'IL', but the longitude is East of -87.5,
                # it's likely mapped to Indianapolis (-86.1) or Ohio. REJECT IT.
                if "IL" in search_query.upper() or "ILLINOIS" in search_query.upper():
                    if location.longitude > -87.5: 
                        print(f"      ⚠️ Rejecting bad match: IL address mapped too far East ({location.longitude})")
                        continue # Skip this result and try the next strategy
                
                cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, ?, ?)", 
                               (clean_key, location.latitude, location.longitude))
                conn.commit()
                return location.latitude, location.longitude
                
        except Exception as e:
            print(f"      ⚠️ Error: {e}")

    # Final Failure
    print(f"      ❌ Give up: {original_addr[:30]}")
    cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon) VALUES (?, 0, 0)", (clean_key,))
    conn.commit()
    return None, None

def generate_map():
    print("🗺️  Initializing Map (Active Snapshot Mode)...")
    conn = get_db_connection()
    ensure_cache_table(conn)
    
    # Load all data
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    
    if df.empty:
        print("   ⚠️ Database is empty. Run the scraper first.")
        return

    # --- 🛡️ ACTIVE SNAPSHOT FILTER 🛡️ ---
    if 'last_seen' not in df.columns:
        print("   ⚠️ Column 'last_seen' missing. Run the scraper once to update your data!")
        return

    # Convert last_seen to datetime
    df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')
    
    # Find the latest time anyone saw ANY trip
    last_run_time = df['last_seen'].max()
    print(f"   🕒 Latest Scrape Data: {last_run_time}")
    
    # Keep trips seen in the last 45 minutes of that time
    cutoff_time = last_run_time - pd.Timedelta(minutes=45)
    active_df = df[df['last_seen'] >= cutoff_time].copy()
    
    print(f"   📉 Mapping {len(active_df)} Active Trips (Hiding {len(df) - len(active_df)} inactive/taken trips).")

    # Load Priorities
    priorities = load_priority_keywords()
    
    # Create Map
    m = folium.Map(location=[40.0, -89.0], zoom_start=7, tiles="CartoDB positron")
    cluster = MarkerCluster().add_to(m)
    
    mapped_count = 0
    
    for _, row in active_df.iterrows():
        pickup = row.get('pickup_address', 'Unknown')
        broker = row.get('broker', 'MTM') 
        miles = row.get('miles', 0)
        payout = row.get('payout', 0) # GET PAYOUT DATA
        
        lat, lon = get_coordinates(conn, pickup)
        
        if lat and lon and lat != 0:
            mapped_count += 1
            is_priority = any(k in pickup.lower() for k in priorities)
            
            # --- DYNAMIC STYLING & TEXT ---
            if broker == 'Modivcare':
                color, icon, prefix = 'green', 'usd', '💰 MODIVCARE'
                # Format price safely
                try:
                    val_display = f"<b>PAYOUT:</b> <span style='color:green; font-size:14px'>${float(payout):.2f}</span>"
                except:
                    val_display = f"<b>PAYOUT:</b> ${payout}"
            else:
                # MTM Default
                if is_priority:
                    color, icon, prefix = 'red', 'star', '🚨 PRIORITY'
                else:
                    color, icon, prefix = 'blue', 'car', '🌊 MTM'
                val_display = f"<b>MILES:</b> {miles}"

            # Construct Popup
            popup = f"""
            <div style="width:200px">
                <b>{prefix}</b><br>
                <b>Date:</b> {row['date']}<br>
                <b>Time:</b> {row['pickup_time']}<br>
                {val_display}<br>
                <hr>
                <b>From:</b> {pickup}<br>
                <b>To:</b> {row.get('dropoff_address', '')}<br>
            </div>
            """
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup, max_width=300),
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(cluster)

    m.save(MAP_OUTPUT)
    conn.close()
    print(f"✅ Map saved to: {MAP_OUTPUT} ({mapped_count} active trips plotted)")

if __name__ == "__main__":
    generate_map()