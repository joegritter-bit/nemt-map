import pandas as pd
import os
from datetime import datetime
from config import HUBS, MIN_PROFIT_PER_HOUR, MAX_SHIFT_HOURS, DB_PATH, ROUTES_FILE, get_logger
from mtm_rates import COUNTY_BASE_RATES

log = get_logger(__name__)

SPRINGFIELD_DRIVERS = []
# Add driver names here as you hire them, e.g.:
# SPRINGFIELD_DRIVERS = ["Driver 1", "Driver 2", "Driver 3"]

SPRINGFIELD_HUB = HUBS["Springfield"]["coords"]
SPRINGFIELD_TARGET_COUNTY = "Sangamon County"


def get_springfield_dispatch():
    if not os.path.exists(ROUTES_FILE):
        return []
    try:
        df = pd.read_csv(ROUTES_FILE)
    except Exception as e:
        log.error(f"Failed to read {ROUTES_FILE}: {e}")
        return []
    if df.empty:
        return []

    today = pd.Timestamp.now().normalize()
    df['Date_Obj'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df[
        (df['Hub'] == 'Springfield') &
        (df['Revenue/Hour'] >= MIN_PROFIT_PER_HOUR) &
        (df['Shift Length (Hrs)'] <= MAX_SHIFT_HOURS) &
        (df['Date_Obj'] >= today)
    ].copy()

    if df.empty:
        return []

    df = df.sort_values(by=['Date_Obj', 'Revenue/Hour'], ascending=[True, False])

    def priority_label(row):
        if row.get('Top County') == SPRINGFIELD_TARGET_COUNTY and row.get('Job Count', 0) >= 3:
            return '🔥 PRIORITY'
        if row.get('Revenue/Hour', 0) >= 45.0:
            return '✅ GOOD'
        return '📋 STANDARD'

    results = []
    # Track which driver+date combos have been assigned (one route per driver per date)
    date_driver_used = {}

    for date, day_group in df.groupby('Date_Obj'):
        date_str = date.strftime('%Y-%m-%d')
        date_driver_used[date_str] = set()
        driver_idx = 0

        for _, row in day_group.iterrows():
            if SPRINGFIELD_DRIVERS:
                # Find next available driver for this date
                assigned = None
                for _ in range(len(SPRINGFIELD_DRIVERS)):
                    candidate = SPRINGFIELD_DRIVERS[driver_idx % len(SPRINGFIELD_DRIVERS)]
                    driver_idx += 1
                    if candidate not in date_driver_used[date_str]:
                        assigned = candidate
                        date_driver_used[date_str].add(candidate)
                        break
                if assigned is None:
                    continue  # all drivers filled for this date
            else:
                assigned = 'Unassigned'

            results.append({
                'Date': row['Date'],
                'Driver': assigned,
                'Priority': priority_label(row),
                'Hub': row.get('Hub', 'Springfield'),
                'Model': row.get('Model', 'Traditional'),
                'Job Count': row.get('Job Count', '?'),
                'Shift Length (Hrs)': row.get('Shift Length (Hrs)', 0),
                'Revenue/Hour': row.get('Revenue/Hour', 0),
                'Total Revenue': row.get('Total Revenue', 0),
                'Top County': row.get('Top County', 'Unknown'),
                'Route Description': row.get('Route Description', 'N/A'),
                'Start Address': row.get('Start Address', 'N/A'),
            })

    return results


def get_springfield_summary():
    routes = get_springfield_dispatch()

    no_drivers = not SPRINGFIELD_DRIVERS
    driver_note = (
        '<p style="color:#c0392b; font-weight:bold;">⚠️ No Springfield drivers registered yet. '
        'Add names to SPRINGFIELD_DRIVERS in springfield_dispatch.py.</p>'
        if no_drivers else ''
    )

    if not routes:
        return (
            f'<p style="font-size:11px; color:#666;">No qualifying Springfield routes found for today or upcoming dates.</p>'
            f'{driver_note}'
        )

    total_rev = sum(float(r.get('Total Revenue', 0)) for r in routes)
    avg_rph = sum(float(r.get('Revenue/Hour', 0)) for r in routes) / len(routes)
    priority_count = sum(1 for r in routes if r['Priority'] == '🔥 PRIORITY')

    return (
        f'<p style="font-size:11px; color:#333;">'
        f'<b>{len(routes)}</b> Springfield route(s) available — '
        f'<b>{priority_count}</b> Sangamon County priority run(s). '
        f'Total potential revenue: <b style="color:green;">${total_rev:,.2f}</b>. '
        f'Average Rev/Hr: <b style="color:green;">${avg_rph:.2f}</b>.'
        f'</p>'
        f'{driver_note}'
    )


if __name__ == '__main__':
    routes = get_springfield_dispatch()
    summary = get_springfield_summary()

    # Strip HTML tags for terminal output
    import re
    clean_summary = re.sub(r'<[^>]+>', '', summary)
    print(f'\n📍 Springfield Dispatch Summary\n{clean_summary.strip()}\n')

    if not routes:
        print('No Springfield routes found.')
    else:
        header = f"{'Date':<12} {'Driver':<15} {'Priority':<14} {'Model':<12} {'Jobs':>4} {'Hrs':>5} {'Rev/Hr':>8} {'Total':>9} {'Top County':<20} Route"
        print(header)
        print('-' * len(header))
        for r in routes:
            print(
                f"{r['Date']:<12} {str(r['Driver']):<15} {r['Priority']:<14} "
                f"{r['Model']:<12} {str(r['Job Count']):>4} "
                f"{str(r['Shift Length (Hrs)']):>5} "
                f"${float(r['Revenue/Hour']):>7.2f} "
                f"${float(r['Total Revenue']):>8.2f} "
                f"{str(r['Top County']):<20} "
                f"{str(r['Route Description'])[:60]}"
            )

        out_file = 'springfield_routes.csv'
        pd.DataFrame(routes).to_csv(out_file, index=False)
        print(f'\n📄 Saved to {out_file}')
