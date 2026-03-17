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
ROUTES_FILE = 'potential_routes.csv'

# 🏭 HUB COORDINATES
HUBS = {
    "Effingham": (39.1200, -88.5434),   
    "Springfield": (39.8017, -89.6680)  
}

# 💰 CONTRACT DATA
MTM_MILEAGE_RATE = 1.50
MILEAGE_BAND_LIMIT = 5.0
COUNTY_BASE_RATES = {
    "Coles County": 40.00, "Fayette County": 40.00, "Clay County": 40.00,
    "Marion County": 50.00, "Jefferson County": 50.00,
    "Christian County": 35.00, "Macon County": 35.00, "Piatt County": 35.00, "Champaign County": 35.00,
    "Sangamon County": 65.00, "Vermilion County": 65.00, "Edgar County": 40.00, "Clark County": 40.00
}
STANDARD_BASE_RATE = 20.00
AFTER_HOURS_BASE_RATE = 20.00

# 🏗️ CITY LOOKUP
CITY_COUNTY_MAP = {
    "springfield": "Sangamon County", "chatham": "Sangamon County",
    "mattoon": "Coles County", "charleston": "Coles County", "oakland": "Coles County",
    "decatur": "Macon County", "champaign": "Champaign County",
    "urbana": "Champaign County", "danville": "Vermilion County",
    "effingham": "Effingham County", "vandalia": "Fayette County",
    "centralia": "Marion County", "salem": "Marion County",
    "mt vernon": "Jefferson County", "mt. vernon": "Jefferson County",
    "taylorville": "Christian County", "monticello": "Piatt County",
    "louisville": "Clay County", "flora": "Clay County",
    "paris": "Edgar County", "casey": "Clark County", "marshall": "Clark County"
}

# Geocoding
geolocator = Nominatim(user_agent="jgritter_nemt_map_v10_31", timeout=15)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)
reverse_service = RateLimiter(geolocator.reverse, min_delay_seconds=1.5)
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

def get_db_connection(): return sqlite3.connect(DB_PATH)

def load_priority_keywords():
    if not os.path.exists(CLINICS_FILE): return []
    with open(CLINICS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip().lower() for line in f if line.strip()]

def ensure_cache_table(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS geo_cache (address TEXT PRIMARY KEY, lat REAL, lon REAL, county TEXT)')
    conn.commit()

def estimate_mtm_price(row, cached_county):
    pickup_addr = str(row.get('pickup_address', '')).lower()
    c_county = str(cached_county).strip()
    current_county = "Unknown" if c_county.lower() in ['nan', 'none', '', 'unknown'] else c_county
    
    if current_county == "Unknown":
        for city, county_name in CITY_COUNTY_MAP.items():
            if city in pickup_addr.replace(',', ' '):
                current_county = county_name
                break

    try:
        pickup_time = pd.to_datetime(row['pickup_time'])
        is_after = pickup_time.hour < 6 or pickup_time.hour >= 18
    except: is_after = False
    
    base = AFTER_HOURS_BASE_RATE if is_after else COUNTY_BASE_RATES.get(current_county, STANDARD_BASE_RATE)
    miles = float(row.get('miles', 0))
    billable_miles = max(0, miles - MILEAGE_BAND_LIMIT)
    return round(base + (billable_miles * MTM_MILEAGE_RATE), 2)

def force_illinois_context(addr):
    if not addr: return ""
    if re.search(r'\bIL\b|\bIllinois\b', addr, re.IGNORECASE): return addr
    zip_match = re.search(r'(\d{5})$', addr)
    if zip_match: return addr[:zip_match.start()] + " IL " + addr[zip_match.start():]
    return f"{addr}, Illinois"

def clean_address_severe(addr):
    if not addr: return ""
    addr = re.split(r' Apt | Unit | Ste | Lot | Bldg | Rm | #', addr, flags=re.IGNORECASE)[0]
    addr = re.sub(r'(\d{5})-\d{4}', r'\1', addr)
    addr = re.sub(r'PO BOX \d+', '', addr, flags=re.IGNORECASE)
    addr = addr.replace(', ,', ',').strip(', ')
    return addr.strip()

def get_county_from_coord(lat, lon):
    try:
        location = reverse_service((lat, lon), language='en')
        if location: return location.raw.get('address', {}).get('county', 'Unknown')
    except: return "Unknown"

def get_coordinates_and_county(conn, original_addr):
    cursor = conn.cursor()
    clean_key = original_addr.replace('\n', ' ').strip()
    
    # 1. Exact Match
    cursor.execute("SELECT lat, lon, county FROM geo_cache WHERE address = ?", (clean_key,))
    res = cursor.fetchone()
    if res and res[0] != 0: return res[0], res[1], res[2]

    # 2. Fuzzy Match
    cursor.execute("SELECT lat, lon, county FROM geo_cache WHERE address LIKE ? LIMIT 1", (clean_key + '%',))
    res = cursor.fetchone()
    if res and res[0] != 0: return res[0], res[1], res[2]

    # 3. Live Geocoding
    base_clean = clean_address_severe(clean_key)
    strategies = [force_illinois_context(base_clean)]
    parts = base_clean.split(',')
    if len(parts) >= 2: strategies.append(force_illinois_context(",".join(parts[-2:]).strip()))

    for query in strategies:
        try:
            loc = geocode_service(query, country_codes='us', viewbox=MIDWEST_VIEWBOX, bounded=True)
            if loc and loc.longitude <= -87.5:
                county = get_county_from_coord(loc.latitude, loc.longitude)
                cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon, county) VALUES (?, ?, ?, ?)", 
                               (clean_key, loc.latitude, loc.longitude, county))
                conn.commit()
                return loc.latitude, loc.longitude, county
        except: pass

    return None, None, "Unknown"

def generate_map():
    print("🗺️  Generating Map v10.31 (Robust CSV Reading)...")
    conn = get_db_connection()
    ensure_cache_table(conn)
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    if df.empty: return

    # --- SETUP MAP ---
    df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')
    cutoff = df['last_seen'].max() - pd.Timedelta(minutes=45)
    active_df = df[df['last_seen'] >= cutoff].copy()
    active_df['dt_sort'] = pd.to_datetime(active_df['date'], errors='coerce')
    active_df = active_df.sort_values('dt_sort')
    
    cache_df = pd.read_sql_query("SELECT address, county FROM geo_cache", conn)
    county_map = {k: v for k, v in zip(cache_df['address'], cache_df['county']) if str(v).lower() != 'nan'}
    priorities = load_priority_keywords()
    
    m = folium.Map(location=[39.4, -89.0], zoom_start=8, tiles="CartoDB positron")

    # --- 1. PLOT STANDARD TRIPS ---
    for single_date in active_df['date'].unique():
        day_data = active_df[active_df['date'] == single_date]
        cluster = MarkerCluster(name=f"📅 {single_date} ({len(day_data)})").add_to(m)
        
        for _, row in day_data.iterrows():
            pickup = row.get('pickup_address', 'Unknown')
            lat, lon, cached_county = get_coordinates_and_county(conn, pickup)
            
            if lat and lon:
                broker = row.get('broker', 'MTM')
                db_county = county_map.get(pickup.replace('\n', ' ').strip(), cached_county)
                is_priority = any(k in pickup.lower() for k in priorities)
                
                if broker == 'Modivcare':
                    price_str = f"${float(row.get('payout', 0)):.2f}"
                    color, icon, prefix = 'green', 'usd', '💰 MODIVCARE'
                else:
                    est = estimate_mtm_price(row, db_county)
                    price_str = f"Est. ${est:.2f}"
                    color = 'red' if is_priority else 'blue'
                    icon = 'star' if is_priority else 'car'
                    prefix = '🚨 PRIORITY' if is_priority else '🌊 MTM'

                popup = f"""
                <div style="width:200px">
                    <b style="color:{color}">{prefix}</b><br>
                    <b style="font-size:16px;">{price_str}</b><br>
                    Time: {row['pickup_time']}<br>
                    Miles: {row.get('miles', 0)}
                </div>
                """
                folium.Marker([lat, lon], popup=folium.Popup(popup, max_width=300),
                              icon=folium.Icon(color=color, icon=icon, prefix='fa')).add_to(cluster)

    # --- 2. PLOT STRATEGIC ROUTES (Grouped by Date) ---
    if os.path.exists(ROUTES_FILE):
        try:
            r_df = pd.read_csv(ROUTES_FILE)
            # FORCE DATE PARSING to ensure they sort and display correctly
            r_df['Date'] = pd.to_datetime(r_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            route_count = 0
            for route_date in sorted(r_df['Date'].unique()):
                daily_routes = r_df[r_df['Date'] == route_date]
                if daily_routes.empty: continue
                
                # Create Layer with show=False so it doesn't clutter, but exists
                routes_group = folium.FeatureGroup(name=f"🚀 Routes: {route_date}", show=False).add_to(m)
                
                for _, row in daily_routes.iterrows():
                    route_count += 1
                    raw_desc = str(row['Route Description'])
                    # Robust Address Extraction
                    addr_match = raw_desc.split('(')[0].strip()
                    hub_name = row.get('Hub', 'Effingham')
                    
                    lat, lon, _ = get_coordinates_and_county(conn, addr_match)
                    
                    if lat and lon:
                        hub_coords = HUBS.get(hub_name)
                        marker_color = 'purple' if hub_name == 'Effingham' else 'orange'
                        
                        popup = f"""
                        <div style="width:220px; border-left: 5px solid {marker_color}; padding-left: 10px;">
                            <h4 style="margin:0; color:{marker_color};">🚀 STRATEGY</h4>
                            <b>Hub: {hub_name}</b><br>
                            Profit: <b style="color:green;">${row['Total Revenue']}</b><br>
                            Hrly: <b>${row.get('Revenue/Hour', '0')}/hr</b><br>
                            <i style="font-size:11px">{raw_desc}</i>
                        </div>
                        """
                        
                        folium.Marker(
                            [lat, lon], 
                            popup=folium.Popup(popup, max_width=300),
                            icon=folium.Icon(color=marker_color, icon='rocket', prefix='fa')
                        ).add_to(routes_group)

                        if hub_coords:
                            folium.PolyLine(
                                locations=[hub_coords, (lat, lon)],
                                color="gray", weight=2.5, opacity=0.7, dash_array='5, 10'
                            ).add_to(routes_group)
            
            print(f"   -> Plotted {route_count} Strategic Routes successfully.")

        except Exception as e: print(f"⚠️ Error plotting routes: {e}")

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(MAP_OUTPUT)
    
    # Toggle Injection
    with open(MAP_OUTPUT, "r", encoding='utf-8') as f: html = f.read()
    inject = """<script>document.addEventListener("DOMContentLoaded", function() { setTimeout(function() { var c = document.querySelector(".leaflet-control-layers-list"); if (!c) return; var d = document.createElement("div"); d.style.cssText = "padding:8px; text-align:center; border-bottom:1px solid #ccc; margin-bottom:5px;"; var h = document.createElement("a"); h.innerHTML = "❌ Hide Trips"; h.href = "#"; h.style.cssText = "cursor:pointer; margin-right:15px; text-decoration:none; color:#c0392b; font-weight:bold;"; h.onclick = function(e) { e.preventDefault(); document.querySelectorAll(".leaflet-control-layers-selector").forEach(i => { if(i.nextSibling.innerText.includes('📅') && i.checked) i.click(); }); }; var s = document.createElement("a"); s.innerHTML = "✅ Show Trips"; s.href = "#"; s.style.cssText = "cursor:pointer; text-decoration:none; color:#27ae60; font-weight:bold;"; s.onclick = function(e) { e.preventDefault(); document.querySelectorAll(".leaflet-control-layers-selector").forEach(i => { if(i.nextSibling.innerText.includes('📅') && !i.checked) i.click(); }); }; d.appendChild(h); d.appendChild(s); c.insertBefore(d, c.firstChild); }, 1000); });</script>"""
    if "</body>" in html:
        with open(MAP_OUTPUT, "w", encoding='utf-8') as f: f.write(html.replace("</body>", inject + "</body>"))

    conn.close()
    print(f"✅ Full Map v10.31 saved.")

if __name__ == "__main__": generate_map()