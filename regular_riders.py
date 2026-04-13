import re
import json
import sqlite3
import os
import pandas as pd
from datetime import datetime

from config import DB_PATH, get_logger

log = get_logger(__name__)
DRIVER_FILE = 'driver_schedule.csv'


def normalize_address(addr):
    """Strip apartment/unit suffixes and normalize for matching."""
    if not addr or not isinstance(addr, str):
        return ""
    addr = re.split(
        r',?\s*(apt|unit|ste|suite|#|lot|bldg|rm|apt\.)\s*\S*',
        addr, flags=re.IGNORECASE)[0]
    addr = addr.strip().lower()
    addr = re.sub(r'\s+', ' ', addr)
    return addr


def addresses_match(addr1, addr2):
    """
    Strict matching — street number, street name prefix, AND city
    must all agree. Prevents false positives from common street names.
    """
    n1 = normalize_address(addr1)
    n2 = normalize_address(addr2)
    if not n1 or not n2:
        return False

    # Both must start with a street number and it must match exactly
    num1 = re.match(r'^(\d+)', n1)
    num2 = re.match(r'^(\d+)', n2)
    if not num1 or not num2:
        return False
    if num1.group(1) != num2.group(1):
        return False

    # Street name prefix (first 6 chars after the number) must match
    street1 = n1[len(num1.group(1)):].strip()[:12]
    street2 = n2[len(num2.group(1)):].strip()[:12]
    if len(street1) < 4 or len(street2) < 4:
        return False
    if not street2.startswith(street1[:6]) and not street1.startswith(street2[:6]):
        return False

    # City must match if both addresses contain one
    city1_m = re.search(r',\s*([^,]+)\s+[Ii][Ll]', addr1 or '')
    city2_m = re.search(r',\s*([^,]+)\s+[Ii][Ll]', addr2 or '')
    if city1_m and city2_m:
        city1 = city1_m.group(1).strip().lower()
        city2 = city2_m.group(1).strip().lower()
        if city1 != city2 and city1 not in city2 and city2 not in city1:
            return False

    return True


def get_regular_rider_alerts():
    """
    Cross-reference driver_schedule.csv pickup addresses against
    today's active marketplace trips. Returns list of matches.
    """
    if not os.path.exists(DRIVER_FILE):
        log.warning(f"Driver schedule not found at {DRIVER_FILE}")
        return []

    # Load regular rider addresses from schedule
    try:
        sched = pd.read_csv(DRIVER_FILE)
        sched.columns = sched.columns.str.strip()
        regular_pickups = sched['PU Address'].dropna().unique().tolist()
        log.info(f"Loaded {len(regular_pickups)} regular rider addresses from schedule")
    except Exception as e:
        log.warning(f"Failed to load driver schedule: {e}")
        return []

    if not regular_pickups:
        return []

    # Load active marketplace trips from DB
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        conn.close()
    except Exception as e:
        log.warning(f"Failed to read trips DB: {e}")
        return []

    if df.empty:
        return []

    # Apply freshness filter
    time_col = 'last_seen' if 'last_seen' in df.columns else 'timestamp'
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    latest = df[time_col].max()
    df = df[df[time_col] >= (latest - pd.Timedelta(minutes=150))].copy()

    if df.empty:
        return []

    today_str = datetime.now().strftime('%Y-%m-%d')

    alerts = []
    for _, trip in df.iterrows():
        pickup = trip.get('pickup_address', '')
        if not pickup:
            continue
        # Skip addresses without a valid multi-digit street number
        if not re.match(r'^\d{2,}', pickup.strip()):
            continue

        for sched_addr in regular_pickups:
            if addresses_match(pickup, sched_addr):
                date_str = str(trip.get('date', ''))
                urgency = 'TODAY' if date_str == today_str else 'UPCOMING'
                log.warning(f"Regular rider on marketplace: {pickup} at {trip.get('pickup_time', '?')}")
                alerts.append({
                    'trip_id':                 trip.get('trip_id', '?'),
                    'date':                    date_str,
                    'pickup_time':             trip.get('pickup_time', ''),
                    'pickup_address':          pickup,
                    'dropoff_address':         trip.get('dropoff_address', ''),
                    'miles':                   trip.get('miles', ''),
                    'broker':                  trip.get('broker', 'MTM'),
                    'matched_schedule_address': sched_addr,
                    'urgency':                 urgency,
                })
                break  # one match per trip is enough

    # Sort: TODAY first, then by pickup_time
    alerts.sort(key=lambda x: (0 if x['urgency'] == 'TODAY' else 1, x['pickup_time']))

    # Export regular pickup addresses to JSON for GitHub Pages (served to Chrome extension)
    export_path = '/home/joegritter/nemt-map/regular_riders.json'
    try:
        with open(export_path, 'w') as f:
            json.dump({
                "addresses": regular_pickups,
                "updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }, f, indent=2)
        log.info(f"Exported {len(regular_pickups)} regular rider addresses to extension")
    except Exception as e:
        log.warning(f"Failed to export regular riders JSON: {e}")

    return alerts


if __name__ == "__main__":
    alerts = get_regular_rider_alerts()
    if alerts:
        print(f"⚡ Found {len(alerts)} regular rider alerts!")
        for a in alerts:
            print(f"  {a['urgency']} | {a['pickup_time']} | {a['pickup_address']}")
    else:
        print("✅ No regular riders on marketplace right now.")
