import pandas as pd
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# --- CONFIG ---
HUB_ADDRESS = "506 South St, Effingham, IL 62401"
OUTPUT_FILE = "Rate_Negotiation_Sheet_Peoria_Radius.csv"

# --- THE FORMULA (Reverse Engineered from your Contract) ---
def calculate_target_rate(miles):
    if miles <= 35: return 40.00   # Tier 1 (Neighbors)
    if miles <= 65: return 50.00   # Tier 2 (Mid-Range)
    if miles <= 95: return 65.00   # Tier 3 (Long-Haul)
    if miles <= 135: return 80.00  # Tier 4 (Extreme / Peoria Range)
    return 100.00                  # Tier 5 (Ultra Long)

# --- TARGET COUNTIES (Non-Contracted & Underpaid) ---
TARGETS = {
    # --- IMMEDIATE NEIGHBORS (Target: $40) ---
    "Cumberland": "Toledo, IL",
    "Shelby": "Shelbyville, IL",
    "Jasper": "Newton, IL",
    "Effingham (Home)": "Effingham, IL",
    
    # --- MID-RANGE (Target: $50) ---
    "Crawford": "Robinson, IL",
    "Richland": "Olney, IL",
    "Wayne": "Fairfield, IL",
    "Bond": "Greenville, IL",
    "Montgomery": "Hillsboro, IL",
    "Moultrie": "Sullivan, IL",
    "Douglas": "Tuscola, IL",
    "Fayette": "Vandalia, IL", # Re-confirming
    "Clay": "Louisville, IL",   # Re-confirming
    
    # --- LONG RANGE (Target: $65) ---
    "Lawrence": "Lawrenceville, IL",
    "Edwards": "Albion, IL",
    "Wabash": "Mount Carmel, IL",
    "White": "Carmi, IL",
    "Hamilton": "McLeansboro, IL",
    "Franklin": "Benton, IL",
    "Perry": "Pinckneyville, IL",
    "De Witt": "Clinton, IL",
    "Logan": "Lincoln, IL",
    "Morgan": "Jacksonville, IL",
    "Christian": "Taylorville, IL", # Negotiate up from $35
    "Macon": "Decatur, IL",         # Negotiate up from $35
    "Piatt": "Monticello, IL",      # Negotiate up from $35
    "Champaign": "Urbana, IL",      # Negotiate up from $35
    "Macoupin": "Carlinville, IL",  # NEW
    "Clinton": "Carlyle, IL",       # NEW
    "Washington": "Nashville, IL",  # NEW
    "Randolph": "Chester, IL",      # NEW (South edge)

    # --- PEORIA RADIUS & NORTH (Target: $80+) ---
    "McLean": "Bloomington, IL",    # Critical Bridge to Peoria
    "Tazewell": "Pekin, IL",        # Peoria Neighbor
    "Peoria": "Peoria, IL",         # The Target
    "Woodford": "Eureka, IL",       # Peoria Neighbor
    "Mason": "Havana, IL",          # Route to Peoria
    "Menard": "Petersburg, IL",     # Route to Peoria
    "Cass": "Virginia, IL",         # West of Springfield
    "Fulton": "Lewistown, IL",      # West of Peoria
    "Knox": "Galesburg, IL",        # Past Peoria (Tier 5?)
    "Livingston": "Pontiac, IL",    # North of Bloomington
    "Ford": "Paxton, IL",           # East of Bloomington
    "Iroquois": "Watseka, IL",      # Far East
}

# --- CURRENT RATES (For Comparison) ---
CURRENT_STANDARD_BASE = 20.00 

def generate_negotiation_sheet():
    print(f"📍 Calculating distances from Hub: {HUB_ADDRESS}...")
    
    geolocator = Nominatim(user_agent="jgritter_rate_negotiator_v2")
    hub_loc = geolocator.geocode(HUB_ADDRESS)
    
    if not hub_loc:
        print("❌ Error: Could not find Hub address.")
        return

    hub_coords = (hub_loc.latitude, hub_loc.longitude)
    results = []

    print(f"📊 Analyzing {len(TARGETS)} Counties out to Peoria Radius...")
    
    for county, seat_city in TARGETS.items():
        try:
            loc = geolocator.geocode(seat_city)
            if loc:
                coords = (loc.latitude, loc.longitude)
                distance = geodesic(hub_coords, coords).miles
                
                # Apply Formula
                target_rate = calculate_target_rate(distance)
                
                # Calculate Lift
                lift = target_rate - CURRENT_STANDARD_BASE
                
                # Zone Labeling
                if distance <= 35: zone = "1 (Local)"
                elif distance <= 65: zone = "2 (Mid)"
                elif distance <= 95: zone = "3 (Long)"
                else: zone = "4 (Extended)"

                results.append({
                    "Zone": zone,
                    "County": county,
                    "County Seat": seat_city,
                    "Hub Dist (mi)": round(distance, 1),
                    "Current Base": f"${CURRENT_STANDARD_BASE:.2f}",
                    "Target Base": f"${target_rate:.2f}",
                    "Increase": f"+${lift:.2f}",
                    "Reasoning": f"Zone {zone} Pricing ({int(distance)} mi from Hub)"
                })
                print(f"   ✅ {county}: {int(distance)} mi -> Target ${target_rate}")
            
            time.sleep(1) # Be nice to the API
            
        except Exception as e:
            print(f"   ⚠️ Error with {county}: {e}")

    # Create DataFrame and Save
    df = pd.DataFrame(results)
    
    # Sort by Distance (closest to farthest)
    df = df.sort_values(by="Hub Dist (mi)", ascending=True)
    
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n📄 Negotiation Sheet Saved: {OUTPUT_FILE}")
    print("💡 Tip: Use the 'Zone' column to explain the tiered logic to the broker.")

if __name__ == "__main__":
    generate_negotiation_sheet()