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
geolocator = Nominatim(user_agent="jgritter_nemt_map_v5", timeout=15)
geocode_service = RateLimiter(geolocator.geocode, min_delay_seconds=1.5)

# 📦 THE MIDWEST CAGE (Iron Dome Settings)
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

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
                # 🛑 SANITY CHECK: IL Border Logic
                if "IL" in search_query.upper() or "ILLINOIS" in search_query.upper():
                    if location.longitude > -87.5: 
                        print(f"      ⚠️ Rejecting bad match: IL address mapped too far East ({location.longitude})")
                        continue 
                
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
    print("🗺️  Initializing Map (Layered + Toggle Buttons)...")
    conn = get_db_connection()
    ensure_cache_table(conn)
    
    # Load all data
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    
    if df.empty:
        print("   ⚠️ Database is empty. Run the scraper first.")
        return

    # --- 🛡️ ACTIVE SNAPSHOT FILTER ---
    if 'last_seen' not in df.columns:
        print("   ⚠️ Column 'last_seen' missing. Run the scraper once to update your data!")
        return

    df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')
    last_run_time = df['last_seen'].max()
    print(f"   🕒 Latest Scrape Data: {last_run_time}")
    
    cutoff_time = last_run_time - pd.Timedelta(minutes=45)
    active_df = df[df['last_seen'] >= cutoff_time].copy()
    
    print(f"   📉 Mapping {len(active_df)} Active Trips (Hiding {len(df) - len(active_df)} inactive/taken trips).")

    # Sort so layers appear in order in the menu
    active_df['dt_sort'] = pd.to_datetime(active_df['date'], errors='coerce')
    active_df = active_df.sort_values('dt_sort')

    priorities = load_priority_keywords()
    
    # Base Map
    m = folium.Map(location=[40.0, -89.0], zoom_start=7, tiles="CartoDB positron")

    # --- 📅 DATE LOOP START ---
    unique_dates = active_df['date'].unique()
    mapped_count = 0
    
    for single_date in unique_dates:
        # Filter data for just this one day
        day_data = active_df[active_df['date'] == single_date]
        
        # Create a specific Cluster for this day
        layer_label = f"📅 {single_date} ({len(day_data)})"
        cluster = MarkerCluster(name=layer_label).add_to(m)
        
        for _, row in day_data.iterrows():
            pickup = row.get('pickup_address', 'Unknown')
            broker = row.get('broker', 'MTM') 
            miles = row.get('miles', 0)
            payout = row.get('payout', 0)
            
            lat, lon = get_coordinates(conn, pickup)
            
            if lat and lon and lat != 0:
                mapped_count += 1
                is_priority = any(k in pickup.lower() for k in priorities)
                
                # --- DYNAMIC STYLING ---
                if broker == 'Modivcare':
                    color, icon, prefix = 'green', 'usd', '💰 MODIVCARE'
                    try: val_display = f"<b>PAYOUT:</b> <span style='color:green; font-size:14px'>${float(payout):.2f}</span>"
                    except: val_display = f"<b>PAYOUT:</b> ${payout}"
                else:
                    if is_priority: color, icon, prefix = 'red', 'star', '🚨 PRIORITY'
                    else: color, icon, prefix = 'blue', 'car', '🌊 MTM'
                    val_display = f"<b>MILES:</b> {miles}"

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

    # 🎛️ Add the Layer Control Menu (Top Right)
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(MAP_OUTPUT)
    
    # --- 💉 INJECT "HIDE ALL / SHOW ALL" BUTTONS VIA JAVASCRIPT ---
    # This reads the HTML we just made and adds a script to create the buttons
    with open(MAP_OUTPUT, "r", encoding='utf-8') as f:
        html_content = f.read()

    injection_script = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() { 
            var control = document.querySelector(".leaflet-control-layers-list");
            if (!control) return;
            
            var div = document.createElement("div");
            div.style.padding = "8px";
            div.style.textAlign = "center";
            div.style.borderBottom = "1px solid #ccc";
            div.style.marginBottom = "5px";
            
            var hideAll = document.createElement("a");
            hideAll.innerHTML = "❌ Hide All";
            hideAll.href = "#";
            hideAll.style.cursor = "pointer";
            hideAll.style.marginRight = "15px";
            hideAll.style.textDecoration = "none";
            hideAll.style.color = "#c0392b";
            hideAll.style.fontWeight = "bold";
            hideAll.onclick = function(e) {
                e.preventDefault();
                var inputs = document.querySelectorAll(".leaflet-control-layers-selector");
                inputs.forEach(function(input) { if (input.checked) input.click(); });
            };
            
            var showAll = document.createElement("a");
            showAll.innerHTML = "✅ Show All";
            showAll.href = "#";
            showAll.style.cursor = "pointer";
            showAll.style.textDecoration = "none";
            showAll.style.color = "#27ae60";
            showAll.style.fontWeight = "bold";
            showAll.onclick = function(e) {
                e.preventDefault();
                var inputs = document.querySelectorAll(".leaflet-control-layers-selector");
                inputs.forEach(function(input) { if (!input.checked) input.click(); });
            };
            
            div.appendChild(hideAll);
            div.appendChild(showAll);
            control.insertBefore(div, control.firstChild);
        }, 1000); // Wait 1s for map to load
    });
    </script>
    """
    
    # Inject before the body closes
    if "</body>" in html_content:
        html_content = html_content.replace("</body>", injection_script + "</body>")
        with open(MAP_OUTPUT, "w", encoding='utf-8') as f:
            f.write(html_content)

    conn.close()
    print(f"✅ Layered Map (with Toggle Buttons) saved to: {MAP_OUTPUT} ({mapped_count} trips plotted)")

if __name__ == "__main__":
    generate_map()