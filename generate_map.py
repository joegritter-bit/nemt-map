import sqlite3
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import re
import json

from regular_riders import get_regular_rider_alerts

from config import (DB_PATH, CLINICS_FILE, ROUTES_FILE,
                    MIDWEST_VIEWBOX, HUBS, CITY_COUNTY_MAP,
                    get_logger)
log = get_logger(__name__)

# 🛠 SETTINGS
MAP_OUTPUT = 'nemt_war_room.html'

# 💰 CONTRACT DATA
from mtm_rates import MTM_MILEAGE_RATE, MILEAGE_BAND_LIMIT, STANDARD_BASE_RATE, AFTER_HOURS_BASE_RATE, COUNTY_BASE_RATES

# 📌 COUNTY CENTROIDS FOR MAP LABELS
COUNTY_CENTROIDS = {
    "Sangamon County": {"coords": [39.75, -89.65], "rate": 65.00},
    "Vermilion County": {"coords": [40.19, -87.73], "rate": 65.00},
    "Christian County": {"coords": [39.55, -89.28], "rate": 55.00},
    "Macon County": {"coords": [39.85, -88.96], "rate": 55.00},
    "Piatt County": {"coords": [39.98, -88.58], "rate": 55.00},
    "Champaign County": {"coords": [40.14, -88.19], "rate": 55.00},
    "Marion County": {"coords": [38.65, -88.92], "rate": 50.00},
    "Jefferson County": {"coords": [38.30, -88.92], "rate": 50.00},
    "Coles County": {"coords": [39.52, -88.22], "rate": 40.00},
    "Fayette County": {"coords": [38.98, -89.02], "rate": 40.00},
    "Clay County": {"coords": [38.75, -88.48], "rate": 40.00},
    "Effingham County": {"coords": [39.06, -88.54], "rate": 20.00} # Standard Base Rate
}

# Geocoding
geolocator = Nominatim(user_agent="JoeNEMT_Bot_v1_generate_map", timeout=15)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=2.0, max_retries=3, error_wait_seconds=4)

def get_db_connection(): return sqlite3.connect(DB_PATH, timeout=30)

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
    except Exception as e:
        log.warning(f"[estimate_mtm_price] Could not parse pickup_time: {e}")
        is_after = False
    
    base = AFTER_HOURS_BASE_RATE if is_after else COUNTY_BASE_RATES.get(current_county, STANDARD_BASE_RATE)
    miles = float(row.get('miles', 0))
    billable_miles = max(0, miles - MILEAGE_BAND_LIMIT)
    return round((base + (billable_miles * MTM_MILEAGE_RATE)) * 2, 2)

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

def get_county_from_addr(addr_str):
    addr_lower = str(addr_str).lower()
    for city, county_name in CITY_COUNTY_MAP.items():
        if city in addr_lower:
            return county_name
    return "Unknown"

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
                county = get_county_from_addr(clean_key)
                cursor.execute("INSERT OR REPLACE INTO geo_cache (address, lat, lon, county) VALUES (?, ?, ?, ?)",
                               (clean_key, loc.latitude, loc.longitude, county))
                conn.commit()
                return loc.latitude, loc.longitude, county
        except Exception as e:
            log.warning(f"[geocode] Failed for query '{query}': {e}")

    return None, None, "Unknown"

def parse_route_stops(route_description, start_address):
    """
    Extracts ordered stop addresses from Route Description field.
    Format examples:
      "6:15 AM (400 E Washingto) ➡ 9:00 AM (2700 N Monroe S)"
      "🚌 2x to 303 landma ➡ 11:00 AM (1275 E Logan St)"
      "----- (530 Ne Glen Oak)"

    Returns list of partial address strings in order.
    """
    stops = []

    # Always start with the full Start Address
    if start_address and str(start_address).strip():
        clean = str(start_address).strip().rstrip(',').strip()
        if clean and clean != 'nan':
            stops.append(clean)

    # Extract addresses from parentheses in route description
    matches = re.findall(r'\(([^)]+)\)', str(route_description))
    for m in matches:
        clean = m.strip()
        if re.match(r'^\d+x?$', clean): continue
        if len(clean) < 5: continue
        stops.append(clean)

    # Deduplicate while preserving order
    seen = []
    for s in stops:
        if s not in seen:
            seen.append(s)
    return seen

def fuzzy_match_geocache(partial_addr, geo_cache_dict):
    """
    Matches a truncated address like '400 E Washingto' against
    full geocached addresses like '400 E Washington St, apt m2'.
    Returns (lat, lon) or (None, None).
    """
    if not partial_addr:
        return None, None

    partial_lower = partial_addr.lower().strip()

    # Try exact match first
    if partial_addr in geo_cache_dict:
        return geo_cache_dict[partial_addr]

    # Try partial string match — find geocache entries that START with
    # the partial address (first 12+ chars)
    prefix = partial_lower[:12]
    candidates = [
        (addr, coords) for addr, coords in geo_cache_dict.items()
        if addr.lower().startswith(prefix) and coords[0] is not None
    ]

    if candidates:
        best = max(candidates,
                   key=lambda x: len(os.path.commonprefix(
                       [partial_lower, x[0].lower()])))
        return best[1]

    return None, None

def generate_map():
    print("🗺️  Generating Map v10.35 (Route Fixes, Date Toggles & Base Rates)...")
    conn = get_db_connection()
    try:
        _generate_map_inner(conn)
    finally:
        conn.commit()
        conn.close()

def _generate_map_inner(conn):
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

    # Full geocache as coord dict for fuzzy matching
    coords_df = pd.read_sql_query(
        "SELECT address, lat, lon FROM geo_cache WHERE lat != 0 AND lat IS NOT NULL", conn)
    geo_cache_dict = {
        row['address']: (row['lat'], row['lon'])
        for _, row in coords_df.iterrows()
    }
    priorities = load_priority_keywords()
    
    # Pre-load geocache to avoid live API calls for known addresses
    full_coords_df = pd.read_sql_query(
        "SELECT address, lat, lon, county FROM geo_cache WHERE lat != 0 AND lat IS NOT NULL", conn)
    local_geo_map = {
        row['address']: (row['lat'], row['lon'], row['county'])
        for _, row in full_coords_df.iterrows()
    }

    m = folium.Map(location=[39.4, -89.0], zoom_start=8, tiles="CartoDB positron")

    # --- 1. PLOT STANDARD TRIPS ---
    for single_date in active_df['date'].unique():
        day_data = active_df[active_df['date'] == single_date]
        cluster = MarkerCluster(name=f"📅 {single_date} ({len(day_data)})").add_to(m)

        for _, row in day_data.iterrows():
            pickup = row.get('pickup_address', 'Unknown')
            dropoff = row.get('dropoff_address', 'Unknown')
            if pickup in local_geo_map:
                lat, lon, cached_county = local_geo_map[pickup]
            else:
                continue  # Skip uncached — don't hit live API
            
            if lat and lon:
                broker = row.get('broker', 'MTM')
                db_county = county_map.get(pickup.replace('\n', ' ').strip(), cached_county)
                is_priority = any(k in pickup.lower() for k in priorities)
                
                if broker == 'Modivcare':
                    price_str = f"RT ${float(row.get('payout', 0)):.2f}"
                    color, icon, prefix = 'green', 'usd', '💰 MODIVCARE'
                else:
                    est = estimate_mtm_price(row, db_county)
                    price_str = f"Est. RT ${est:.2f}"
                    color = 'red' if is_priority else 'blue'
                    icon = 'star' if is_priority else 'car'
                    prefix = '🚨 PRIORITY' if is_priority else '🌊 MTM'

                popup = f"""
                <div style="width:200px">
                    <b style="color:{color}">{prefix}</b><br>
                    <b style="font-size:16px;">{price_str}</b><br>
                    Date: {row['date']}<br>
                    Pick Up: {pickup}<br>
                    Drop Off: {dropoff}<br>
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
            r_df['Date'] = pd.to_datetime(
                r_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

            ROUTE_COLORS = [
                '#e74c3c', '#3498db', '#2ecc71', '#f39c12',
                '#9b59b6', '#1abc9c', '#e67e22', '#e91e63'
            ]

            for route_date in sorted(r_df['Date'].unique()):
                daily_routes = r_df[r_df['Date'] == route_date]
                if daily_routes.empty: continue

                routes_group = folium.FeatureGroup(
                    name=f"🚀 Routes: {route_date}",
                    show=False
                ).add_to(m)

                for route_idx, (_, row) in enumerate(daily_routes.iterrows()):

                    hub_name = row.get('Hub', 'Effingham')
                    hub_coords = HUBS.get(hub_name, {}).get('coords')
                    model = row.get('Model', 'Traditional')
                    color = ROUTE_COLORS[route_idx % len(ROUTE_COLORS)]
                    is_clinic = model == 'Clinic'

                    # Parse all stops in order
                    stops = parse_route_stops(
                        row.get('Route Description', ''),
                        row.get('Start Address', '')
                    )

                    # Geocode each stop using fuzzy match
                    stop_coords = []
                    for stop in stops:
                        lat, lon = fuzzy_match_geocache(stop, geo_cache_dict)
                        if lat and lon:
                            stop_coords.append((lat, lon, stop))

                    if not stop_coords:
                        continue

                    # Build full route: hub → stop1 → stop2 → ... → hub
                    full_route = []

                    if hub_coords:
                        full_route.append(hub_coords)

                    for i, (lat, lon, stop_name) in enumerate(stop_coords):
                        full_route.append((lat, lon))
                        if is_clinic and i < len(stop_coords) - 1:
                            pass  # clinic riders share same destination

                    if hub_coords:
                        full_route.append(hub_coords)

                    if len(full_route) < 2:
                        continue

                    # Draw the route polyline
                    folium.PolyLine(
                        locations=full_route,
                        color=color,
                        weight=3.5,
                        opacity=0.85,
                        dash_array='8 4' if is_clinic else None,
                        tooltip=f"{hub_name} | {model} | "
                                f"${row.get('Total Revenue', '?')} | "
                                f"{row.get('Revenue/Hour', '?')}/hr"
                    ).add_to(routes_group)

                    # Direction arrow at midpoint
                    if len(full_route) >= 2:
                        mid_idx = len(full_route) // 2
                        folium.RegularPolygonMarker(
                            location=full_route[mid_idx],
                            number_of_sides=3,
                            radius=6,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.9,
                            rotation=0
                        ).add_to(routes_group)

                    # Hub marker
                    if hub_coords:
                        marker_color = (
                            'purple' if hub_name == 'Effingham' else 'orange'
                        )
                        popup_html = f"""
                        <div style="width:220px;
                                    border-left:5px solid {color};
                                    padding-left:10px;">
                            <h4 style="margin:0; color:{color};">
                                🚀 {hub_name} Route</h4>
                            <b>Model:</b> {model}<br>
                            <b>Jobs:</b> {row.get('Job Count', '?')}<br>
                            <b>Revenue:</b>
                                <b style="color:green;">
                                    ${row.get('Total Revenue', '?')}
                                </b><br>
                            <b>Rate:</b>
                                ${row.get('Revenue/Hour', '?')}/hr<br>
                            <b>Shift:</b>
                                {row.get('Shift Length (Hrs)', 0)} hrs<br>
                            <b>County:</b>
                                {row.get('Top County', 'Unknown')}<br>
                            <hr style="margin:5px 0;">
                            <i style="font-size:11px;">
                                {row.get('Route Description', 'N/A')}
                            </i>
                        </div>
                        """
                        folium.Marker(
                            hub_coords,
                            popup=folium.Popup(popup_html, max_width=300),
                            icon=folium.Icon(
                                color=marker_color,
                                icon='rocket',
                                prefix='fa'
                            )
                        ).add_to(routes_group)

                    # Stop markers along the route
                    for i, (lat, lon, stop_name) in enumerate(stop_coords):
                        stop_label = (
                            '🏥 Clinic' if i == len(stop_coords) - 1 and is_clinic
                            else f'Stop {i+1}'
                        )
                        folium.CircleMarker(
                            location=(lat, lon),
                            radius=7,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=0.8,
                            popup=folium.Popup(
                                f"<b>{stop_label}</b><br>{stop_name}",
                                max_width=200
                            )
                        ).add_to(routes_group)

            print(f"   -> Routes plotted successfully.")

        except Exception as e:
            log.warning(f"Route plotting failed: {e}")
            print(f"⚠️ Error plotting routes: {e}")

    # --- 3. PLOT COUNTY BASE RATE LABELS ---
    rates_group = folium.FeatureGroup(name="💰 County Base Rates", show=True).add_to(m)
    for county, data in COUNTY_CENTROIDS.items():
        # HTML div to create a nice floating label
        label_html = f'''
        <div style="font-size: 10pt; color: #333; font-weight: bold; 
                    background: rgba(255, 255, 255, 0.85); border: 1px solid #777; 
                    border-radius: 4px; padding: 2px 4px; text-align: center;
                    white-space: nowrap; box-shadow: 1px 1px 3px rgba(0,0,0,0.3);">
            {county.replace(" County", "")}<br><span style="color: #27ae60;">${data['rate']:.2f}</span>
        </div>
        '''
        folium.Marker(
            location=data['coords'],
            icon=folium.DivIcon(
                icon_size=(100, 36),
                icon_anchor=(50, 18),
                html=label_html
            )
        ).add_to(rates_group)

    # --- 4. REGULAR RIDER MARKERS ---
    REGULAR_RIDERS_JSON = '/home/joegritter/nemt-map/regular_riders.json'
    try:
        # Load full watchlist
        watchlist = []
        if os.path.exists(REGULAR_RIDERS_JSON):
            with open(REGULAR_RIDERS_JSON) as f:
                data = json.load(f)
            watchlist = data.get('addresses', [])

        # Get live marketplace matches and build a set of matched watchlist addresses
        live_alerts = get_regular_rider_alerts()
        live_matched = {a['matched_schedule_address'] for a in live_alerts}

        if watchlist:
            riders_group = folium.FeatureGroup(
                name='⚡ Regular Riders', show=True).add_to(m)

            for addr in watchlist:
                # Geocode from cache only — no live API calls
                lat, lon = fuzzy_match_geocache(addr, geo_cache_dict)
                if not lat or not lon:
                    continue

                is_live = addr in live_matched

                if is_live:
                    # Find the matching alert for richer tooltip
                    match = next(
                        (a for a in live_alerts
                         if a['matched_schedule_address'] == addr), None)
                    tooltip_lines = ['🚨 ON MARKETPLACE NOW — Accept immediately']
                    if match:
                        tooltip_lines.append(
                            f"{match.get('date','')} {match.get('pickup_time','')}")
                        tooltip_lines.append(
                            f"→ {match.get('dropoff_address','')}")
                        tooltip_lines.append(
                            f"{match.get('broker','MTM')} | {match.get('miles','')} mi")
                    tooltip = ' | '.join(tooltip_lines)
                    marker_icon = folium.Icon(
                        color='red', icon='exclamation', prefix='fa')
                else:
                    tooltip = 'Regular rider address — monitor'
                    marker_icon = folium.Icon(
                        color='lightgray', icon='user', prefix='fa')

                folium.Marker(
                    location=[lat, lon],
                    tooltip=tooltip,
                    popup=folium.Popup(
                        f"<b>{'🚨 ON MARKETPLACE' if is_live else '👤 Regular Rider'}</b>"
                        f"<br>{addr}",
                        max_width=260),
                    icon=marker_icon
                ).add_to(riders_group)

    except Exception as e:
        log.warning(f"Regular rider markers failed: {e}")

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(MAP_OUTPUT)
    
    # Toggle Injection
    with open(MAP_OUTPUT, "r", encoding='utf-8') as f: html = f.read()
    inject = """<script>document.addEventListener("DOMContentLoaded", function() { setTimeout(function() { var c = document.querySelector(".leaflet-control-layers-list"); if (!c) return; var d = document.createElement("div"); d.style.cssText = "padding:8px; text-align:center; border-bottom:1px solid #ccc; margin-bottom:5px;"; var h = document.createElement("a"); h.innerHTML = "❌ Hide Trips"; h.href = "#"; h.style.cssText = "cursor:pointer; margin-right:15px; text-decoration:none; color:#c0392b; font-weight:bold;"; h.onclick = function(e) { e.preventDefault(); document.querySelectorAll(".leaflet-control-layers-selector").forEach(i => { if(i.nextSibling.innerText.includes('📅') && i.checked) i.click(); }); }; var s = document.createElement("a"); s.innerHTML = "✅ Show Trips"; s.href = "#"; s.style.cssText = "cursor:pointer; text-decoration:none; color:#27ae60; font-weight:bold;"; s.onclick = function(e) { e.preventDefault(); document.querySelectorAll(".leaflet-control-layers-selector").forEach(i => { if(i.nextSibling.innerText.includes('📅') && !i.checked) i.click(); }); }; d.appendChild(h); d.appendChild(s); c.insertBefore(d, c.firstChild); }, 1000); });</script>"""
    if "</body>" in html:
        with open(MAP_OUTPUT, "w", encoding='utf-8') as f: f.write(html.replace("</body>", inject + "</body>"))

    print(f"✅ Full Map v10.35 saved.")

if __name__ == "__main__": generate_map()