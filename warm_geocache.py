from config import DB_PATH
import re
import sqlite3, pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import logging

logging.getLogger("geopy").setLevel(logging.CRITICAL)

geolocator = Nominatim(user_agent="JoeNEMT_geocache_warmer", timeout=15)
geocode_service = RateLimiter(
    geolocator.geocode, min_delay_seconds=2.0,
    max_retries=2, error_wait_seconds=4)
MIDWEST_VIEWBOX = [(35.0, -95.0), (44.0, -84.0)]

def warm_cache():
    conn = sqlite3.connect(DB_PATH, timeout=30)

    # Get all uncached trip addresses
    trips = pd.read_sql_query(
        "SELECT DISTINCT pickup_address FROM trips "
        "UNION "
        "SELECT DISTINCT dropoff_address FROM trips", conn)

    cached = pd.read_sql_query("SELECT address FROM geo_cache", conn)
    cached_set = set(cached['address'].tolist())

    missing = [a for a in trips.iloc[:, 0].dropna().tolist()
               if a not in cached_set]

    print(f"📍 {len(cached_set)} already cached")
    print(f"🌍 {len(missing)} addresses need geocoding")
    print(f"⏱️  Estimated time: {len(missing) * 2 / 60:.1f} minutes")

    # Illinois bounding box — reject anything outside this
    IL_LAT_MIN, IL_LAT_MAX = 36.97, 42.51
    IL_LON_MIN, IL_LON_MAX = -91.51, -87.02

    for i, addr in enumerate(missing):
        try:
            clean = addr.replace('\n', ' ').strip()
            # Normalize double-comma gaps (e.g. "APT 1, , City IL") → single comma
            query = re.sub(r',\s*,+', ',', clean)
            loc = geocode_service(
                query + ", Illinois",
                country_codes='us',
                viewbox=MIDWEST_VIEWBOX
            )
            if loc:
                lat, lon = loc.latitude, loc.longitude
                if not (IL_LAT_MIN <= lat <= IL_LAT_MAX and IL_LON_MIN <= lon <= IL_LON_MAX):
                    print(f"   ⚠️ Outside IL bounds ({lat:.3f},{lon:.3f}), skipping: {clean[:40]}")
                    conn.execute(
                        "INSERT OR REPLACE INTO geo_cache "
                        "(address, lat, lon) VALUES (?, 0, 0)",
                        (clean,))
                else:
                    conn.execute(
                        "INSERT OR REPLACE INTO geo_cache "
                        "(address, lat, lon, county) VALUES (?, ?, ?, ?)",
                        (clean, lat, lon, "Unknown"))
            else:
                conn.execute(
                    "INSERT OR REPLACE INTO geo_cache "
                    "(address, lat, lon) VALUES (?, 0, 0)",
                    (clean,))
            if i % 50 == 0:
                conn.commit()
                print(f"   [{i}/{len(missing)}] cached so far...")
        except Exception as e:
            print(f"   ⚠️ Failed: {addr[:30]} — {e}")
            continue

    conn.commit()
    conn.close()
    print(f"✅ Geocache warmed. {len(missing)} new addresses cached.")

if __name__ == "__main__":
    warm_cache()
