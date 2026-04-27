from config import ROUTES_FILE, DB_PATH, get_logger, MIN_PROFIT_PER_HOUR, MAX_SHIFT_HOURS, EXCLUDED_COUNTIES
from regular_riders import get_regular_rider_alerts
import pandas as pd
import sqlite3
import os
from datetime import datetime

log = get_logger(__name__)

_HOME               = os.path.expanduser('~')
DASHBOARD_OUTPUT    = os.path.join(_HOME, 'nemt-map', 'dashboard.html')
SPRINGFIELD_CSV     = os.path.join(_HOME, 'nemt-scraper', 'springfield_routes.csv')
EXTENSIONS_CSV      = os.path.join(_HOME, 'nemt-scraper', 'brandy_overtime.csv')

ACTIVE_WINDOW_MINUTES = 150


def _build_county_map(conn):
    """Load address→county mapping from geo_cache."""
    try:
        cache_df = pd.read_sql_query("SELECT address, county FROM geo_cache", conn)
        return dict(zip(cache_df['address'], cache_df['county']))
    except Exception:
        return {}


def _is_chicago_area(addr, county_map):
    """Return True for trips that should be excluded (Chicago metro area)."""
    if not isinstance(addr, str):
        return False
    if county_map.get(addr, 'Unknown') in EXCLUDED_COUNTIES:
        return True
    addr_lower = addr.lower()
    if 'chicago' in addr_lower and 'il ' in addr_lower:
        return True
    return False


def _load_routes():
    """Return (active_routes, historical_routes).

    Routes are 'active' when potential_routes.csv was written within the last
    ACTIVE_WINDOW_MINUTES minutes — matching the 150-minute freshness window
    used by the email pipeline.  Stale routes are returned separately so the
    dashboard can display them in a secondary section rather than dropping them.
    """
    if not os.path.exists(ROUTES_FILE):
        return [], []
    try:
        file_age_minutes = (datetime.now().timestamp() - os.path.getmtime(ROUTES_FILE)) / 60
        is_fresh = file_age_minutes <= ACTIVE_WINDOW_MINUTES

        df = pd.read_csv(ROUTES_FILE)
        df = df[
            (df['Shift Length (Hrs)'] <= MAX_SHIFT_HOURS)
            & (df['Revenue/Hour'] >= MIN_PROFIT_PER_HOUR)
        ]
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df = df.sort_values(['Date_Obj', 'Revenue/Hour'], ascending=[True, False])
        routes = df.to_dict('records')

        if is_fresh:
            return routes, []
        else:
            return [], routes
    except Exception as e:
        log.warning(f"Failed to load routes: {e}")
        return [], []


def _load_springfield():
    if not os.path.exists(SPRINGFIELD_CSV):
        return [], False
    try:
        file_age_minutes = (datetime.now().timestamp() - os.path.getmtime(SPRINGFIELD_CSV)) / 60
        stale = file_age_minutes > ACTIVE_WINDOW_MINUTES
        return pd.read_csv(SPRINGFIELD_CSV).to_dict('records'), stale
    except Exception as e:
        log.warning(f"Failed to load springfield routes: {e}")
        return [], False


def _load_extensions():
    if not os.path.exists(EXTENSIONS_CSV):
        return [], False
    try:
        file_age_minutes = (datetime.now().timestamp() - os.path.getmtime(EXTENSIONS_CSV)) / 60
        stale = file_age_minutes > ACTIVE_WINDOW_MINUTES
        df = pd.read_csv(EXTENSIONS_CSV)
        return df.sort_values('SortValue', ascending=False).to_dict('records'), stale
    except Exception as e:
        log.warning(f"Failed to load extensions: {e}")
        return [], False




def get_hotspots(limit=6):
    """Top pickup locations by volume in active snapshot (Chicago excluded)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        county_map = _build_county_map(conn)
        conn.close()
        if df.empty:
            return []
        df = df[
            ~df['pickup_address'].apply(lambda a: _is_chicago_area(a, county_map))
            & ~df['dropoff_address'].apply(lambda a: _is_chicago_area(a, county_map))
        ]
        if df.empty:
            return []
        time_col = 'last_seen' if 'last_seen' in df.columns else 'timestamp'
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
        latest = df[time_col].max()
        active = df[df[time_col] >= (latest - pd.Timedelta(minutes=150))]
        if active.empty:
            return []
        active = active.copy()
        active['simple_pickup'] = active['pickup_address'].apply(
            lambda x: x.split(',')[0].strip() if x else 'Unknown')
        top = active['simple_pickup'].value_counts().head(limit)
        results = []
        for addr, count in top.items():
            trips = active[active['simple_pickup'] == addr]
            broker = trips['broker'].mode().iloc[0] if not trips.empty else 'MTM'
            results.append({'address': addr, 'count': count, 'broker': broker})
        return results
    except Exception as e:
        log.warning(f"get_hotspots failed: {e}")
        return []


def get_recurring_patterns(limit=8):
    """Weekly recurring trips — same day/time/location (Chicago excluded)."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        df = pd.read_sql_query("SELECT * FROM trips", conn)
        county_map = _build_county_map(conn)
        conn.close()
        if df.empty:
            return []
        df = df[
            ~df['pickup_address'].apply(lambda a: _is_chicago_area(a, county_map))
            & ~df['dropoff_address'].apply(lambda a: _is_chicago_area(a, county_map))
        ]
        if df.empty:
            return []
        df['simple_pickup'] = df['pickup_address'].apply(
            lambda x: x.split(',')[0].strip() if x else 'Unknown')
        df['day_name'] = pd.to_datetime(df['date'], errors='coerce').dt.day_name()
        recurring = (
            df.groupby(['day_name', 'pickup_time', 'simple_pickup', 'broker'])
            .size()
            .reset_index(name='count')
            .query('count >= 2')
            .sort_values('count', ascending=False)
            .head(limit)
        )
        return recurring.to_dict('records')
    except Exception as e:
        log.warning(f"get_recurring_patterns failed: {e}")
        return []


def generate_dashboard():
    print("📊 Generating team dispatch dashboard...")

    active_routes, historical_routes = _load_routes()
    routes      = active_routes
    springfield, springfield_stale = _load_springfield()
    extensions, extensions_stale   = _load_extensions()
    alerts      = get_regular_rider_alerts()
    hotspots   = get_hotspots()
    patterns   = get_recurring_patterns()

    now          = datetime.now()
    refresh_time = now.strftime('%m/%d/%Y %I:%M %p')

    clinic_routes = [r for r in routes if r.get('Model') == 'Clinic']
    trad_routes   = [r for r in routes if r.get('Model') == 'Traditional']

    # ── Header ────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="1800">
  <title>NEMT Dispatch Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; color: #333; }}
    .header {{
      background: #2c3e50; color: white;
      padding: 16px 20px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    .header h1 {{ font-size: 20px; }}
    .header .meta {{ font-size: 12px; opacity: 0.8; }}
    .map-btn {{
      background: #27ae60; color: white;
      padding: 8px 16px; border-radius: 4px;
      text-decoration: none; font-size: 13px; font-weight: bold;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}
    .section {{
      background: white; border-radius: 8px;
      margin-bottom: 16px; overflow: hidden;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .section-header {{ padding: 12px 16px; color: white; font-weight: bold; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th {{
      background: rgba(0,0,0,0.05);
      padding: 8px 12px; text-align: left;
      font-weight: bold; border-bottom: 1px solid #eee;
    }}
    td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: #f9f9f9; }}
    .revenue {{ color: #27ae60; font-weight: bold; }}
    .priority {{
      background: #ff6b35; color: white;
      padding: 2px 6px; border-radius: 3px;
      font-size: 11px; font-weight: bold;
    }}
    .empty {{ padding: 16px; color: #888; font-style: italic; font-size: 13px; }}
    .alert-row td {{ background: #fff8f0; }}
    .stats-bar {{
      display: flex; gap: 16px; padding: 12px 16px;
      background: #f8f8f8; border-bottom: 1px solid #eee; flex-wrap: wrap;
    }}
    .stat {{ text-align: center; }}
    .stat .val {{ font-size: 20px; font-weight: bold; color: #2c3e50; }}
    .stat .lbl {{ font-size: 11px; color: #888; }}
    @media (max-width: 600px) {{ td, th {{ padding: 6px 8px; font-size: 11px; }} }}
  </style>
</head>
<body>
<div class="header">
  <div>
    <h1>🚗 NEMT Dispatch Dashboard</h1>
    <div class="meta">Last updated: {refresh_time} · Auto-refreshes every 30 min</div>
  </div>
  <a href="https://joegritter-bit.github.io/nemt-map/" class="map-btn" target="_blank">
    🗺️ Live Map
  </a>
  <a href="/nemt-map/dashboard/" class="map-btn" target="_blank">
    📊 Analytics Dashboard
  </a>
  <a href="quote_calc.html" class="map-btn">
    💲 Trip Quote
  </a>
  <a href="http://206.189.190.92:8082" class="map-btn" target="_blank">
    📡 GPS Tracking
  </a>
</div>
<div class="container">
"""

    # ── Stats bar ─────────────────────────────────────────────────────────────
    total_rev = sum(float(r.get('Total Revenue', 0)) for r in routes)
    avg_rph   = (sum(float(r.get('Revenue/Hour', 0)) for r in routes) / len(routes)
                 if routes else 0)
    html += f"""
<div class="section">
  <div class="stats-bar">
    <div class="stat">
      <div class="val">{len(routes)}</div>
      <div class="lbl">Available Shifts</div>
    </div>
    <div class="stat">
      <div class="val" style="color:#27ae60">${total_rev:,.0f}</div>
      <div class="lbl">Total Opportunity</div>
    </div>
    <div class="stat">
      <div class="val">${avg_rph:.0f}/hr</div>
      <div class="lbl">Avg Rev/Hour</div>
    </div>
    <div class="stat">
      <div class="val" style="color:#e74c3c">{len(alerts)}</div>
      <div class="lbl">Regular Rider Alerts</div>
    </div>
  </div>
</div>
"""

    # ── Regular rider alerts ───────────────────────────────────────────────────
    if alerts:
        html += """
<div class="section">
  <div class="section-header" style="background:#e67e22;">
    ⚡ REGULAR RIDERS ON MARKETPLACE — ACCEPT NOW
  </div>
  <p style="padding:8px 16px; font-size:12px; color:#e67e22; font-weight:bold; background:#fff8f0; margin:0;">
    These are your standing-order riders placed back on the marketplace. Accept immediately.
  </p>
  <table>
    <tr>
      <th>⚡</th><th>Date</th><th>Time</th>
      <th>Pickup Address</th><th>Dropoff</th><th>Miles</th><th>Broker</th>
    </tr>
"""
        for a in alerts:
            urgency_badge = '<span class="priority">TODAY</span>' if a.get('urgency') == 'TODAY' else 'Upcoming'
            matched_sub = f'<br><span style="font-size:10px;color:#888;">Matched: {a.get("matched_schedule_address","")}</span>'
            html += f"""
    <tr class="alert-row">
      <td>{urgency_badge}</td>
      <td>{a.get('date', '')}</td>
      <td><b>{a.get('pickup_time', '')}</b></td>
      <td><b>{a.get('pickup_address', '')}</b>{matched_sub}</td>
      <td>{a.get('dropoff_address', '')}</td>
      <td>{a.get('miles', '')}</td>
      <td>{a.get('broker', 'MTM')}</td>
    </tr>"""
        html += "\n  </table>\n</div>"
    else:
        html += """
<div class="section">
  <div class="section-header" style="background:#e67e22;">
    ⚡ Regular Riders on Marketplace
  </div>
  <div class="empty">✅ No regular rider addresses found on marketplace in this snapshot.</div>
</div>"""

    # ── Springfield dispatch ───────────────────────────────────────────────────
    if springfield:
        html += """
<div class="section">
  <div class="section-header" style="background:#1a6b3c;">
    🏙️ Springfield Dispatch
  </div>
"""
        if springfield_stale:
            html += """  <div style="background:#fff3cd; color:#856404; padding:8px 16px; font-size:12px; font-weight:bold; border-bottom:1px solid #ffc107;">
    ⚠️ Data from previous run — Stage 4 may have failed
  </div>
"""
        row_style = ' style="opacity:0.7;"' if springfield_stale else ''
        html += """  <table>
    <tr>
      <th>Date</th><th>Priority</th><th>Model</th>
      <th>Jobs</th><th>Shift</th><th>Rev/Hr</th>
      <th>Total</th><th>Top County</th><th>Route</th>
    </tr>
"""
        for r in springfield:
            html += f"""
    <tr{row_style}>
      <td>{r.get('Date', '')}</td>
      <td>{r.get('Priority', '')}</td>
      <td>{r.get('Model', '')}</td>
      <td>{r.get('Job Count', '')}</td>
      <td>{r.get('Shift Length (Hrs)', '')}h</td>
      <td class="revenue">${float(r.get('Revenue/Hour', 0)):.2f}</td>
      <td class="revenue"><b>${float(r.get('Total Revenue', 0)):.2f}</b></td>
      <td>{r.get('Top County', 'Unknown')}</td>
      <td style="font-size:11px;">{r.get('Route Description', '')}</td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Clinic routes ──────────────────────────────────────────────────────────
    if clinic_routes:
        html += """
<div class="section">
  <div class="section-header" style="background:#e67e22;">
    💊 Clinic Routes (Multi-Load)
  </div>
  <table>
    <tr>
      <th>Date</th><th>Hub</th><th>Jobs</th>
      <th>Shift</th><th>Rev/Hr</th><th>Total</th>
      <th>Top County</th><th>Route</th>
    </tr>
"""
        for r in clinic_routes[:20]:
            is_stale = str(r.get('has_stale_leg', 'False')).strip().lower() in ('true', '1', 'yes')
            stale_badge = ' <span style="color:#e67e22;font-weight:bold;" title="One or more legs may no longer be available">⚠️</span>' if is_stale else ''
            stale_sub = '<br><span style="font-size:10px;color:#e67e22;">⚠️ One or more legs may no longer be available</span>' if is_stale else ''
            html += f"""
    <tr>
      <td>{r.get('Date', '')}</td>
      <td><b>{r.get('Hub', '?')}</b>{stale_badge}</td>
      <td>{r.get('Job Count', '?')}</td>
      <td>{r.get('Shift Length (Hrs)', 0)}h</td>
      <td class="revenue">${float(r.get('Revenue/Hour', 0)):.2f}</td>
      <td class="revenue"><b>${float(r.get('Total Revenue', 0)):.2f}</b></td>
      <td>{r.get('Top County', 'Unknown')}</td>
      <td style="font-size:11px;">{r.get('Route Description', 'N/A')}{stale_sub}</td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Traditional routes ────────────────────────────────────────────────────
    if trad_routes:
        html += """
<div class="section">
  <div class="section-header" style="background:#8e44ad;">
    🏆 Traditional Routes
  </div>
  <table>
    <tr>
      <th>Date</th><th>Hub</th><th>Jobs</th>
      <th>Shift</th><th>Rev/Hr</th><th>Total</th>
      <th>Top County</th><th>Route</th>
    </tr>
"""
        for r in trad_routes[:20]:
            is_stale = str(r.get('has_stale_leg', 'False')).strip().lower() in ('true', '1', 'yes')
            stale_badge = ' <span style="color:#e67e22;font-weight:bold;" title="One or more legs may no longer be available">⚠️</span>' if is_stale else ''
            stale_sub = '<br><span style="font-size:10px;color:#e67e22;">⚠️ One or more legs may no longer be available</span>' if is_stale else ''
            html += f"""
    <tr>
      <td>{r.get('Date', '')}</td>
      <td><b>{r.get('Hub', '?')}</b>{stale_badge}</td>
      <td>{r.get('Job Count', '?')}</td>
      <td>{r.get('Shift Length (Hrs)', 0)}h</td>
      <td class="revenue">${float(r.get('Revenue/Hour', 0)):.2f}</td>
      <td class="revenue"><b>${float(r.get('Total Revenue', 0)):.2f}</b></td>
      <td>{r.get('Top County', 'Unknown')}</td>
      <td style="font-size:11px;">{r.get('Route Description', 'N/A')}{stale_sub}</td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Historical routes (stale CSV — pipeline may not have run recently) ────
    if historical_routes:
        hist_clinic = [r for r in historical_routes if r.get('Model') == 'Clinic']
        hist_trad   = [r for r in historical_routes if r.get('Model') == 'Traditional']
        all_hist    = hist_clinic + hist_trad
        html += """
<div class="section">
  <div class="section-header" style="background:#7f8c8d;">
    🕐 Historical Routes (data older than 150 minutes — pipeline may not have run)
  </div>
  <table>
    <tr>
      <th>Date</th><th>Model</th><th>Hub</th><th>Jobs</th>
      <th>Shift</th><th>Rev/Hr</th><th>Total</th>
      <th>Top County</th><th>Route</th>
    </tr>
"""
        for r in all_hist[:30]:
            html += f"""
    <tr style="opacity:0.7;">
      <td>{r.get('Date', '')}</td>
      <td>{r.get('Model', 'Traditional')}</td>
      <td><b>{r.get('Hub', '?')}</b></td>
      <td>{r.get('Job Count', '?')}</td>
      <td>{r.get('Shift Length (Hrs)', 0)}h</td>
      <td class="revenue">${float(r.get('Revenue/Hour', 0)):.2f}</td>
      <td class="revenue"><b>${float(r.get('Total Revenue', 0)):.2f}</b></td>
      <td>{r.get('Top County', 'Unknown')}</td>
      <td style="font-size:11px;">{r.get('Route Description', 'N/A')}</td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Driver extensions ─────────────────────────────────────────────────────
    if extensions:
        html += """
<div class="section">
  <div class="section-header" style="background:#27ae60;">
    🧩 Driver Schedule Extensions
  </div>
"""
        if extensions_stale:
            html += """  <div style="background:#fff3cd; color:#856404; padding:8px 16px; font-size:12px; font-weight:bold; border-bottom:1px solid #ffc107;">
    ⚠️ Data from previous run — Stage 5 may have failed
  </div>
"""
        row_style = ' style="opacity:0.7;"' if extensions_stale else ''
        html += """  <table>
    <tr>
      <th>Driver</th><th>Day</th><th>Window</th>
      <th>Broker</th><th>Route</th><th>Price</th>
    </tr>
"""
        for m in extensions[:15]:
            html += f"""
    <tr{row_style}>
      <td><b>{m.get('Driver', '?')}</b></td>
      <td>{m.get('Day', '')}</td>
      <td>{m.get('Window', '')}</td>
      <td>{m.get('Broker', 'MTM')}</td>
      <td>{m.get('Route', '')}</td>
      <td class="revenue"><b>{m.get('Price', '')}</b></td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Active hotspots ───────────────────────────────────────────────────────
    if hotspots:
        html += """
<div class="section">
  <div class="section-header" style="background:#d35400;">
    🔥 Active Hotspots
  </div>
  <table>
    <tr><th>Location</th><th>Broker</th><th>Active Trips</th></tr>
"""
        for h in hotspots:
            html += f"""
    <tr>
      <td>{h['address']}</td>
      <td><b>{h['broker']}</b></td>
      <td class="revenue"><b>{h['count']} available</b></td>
    </tr>"""
        html += "\n  </table>\n</div>"

    # ── Weekly recurring patterns ──────────────────────────────────────────────
    if patterns:
        html += """
<div class="section">
  <div class="section-header" style="background:#34495e;">
    🔄 Weekly Recurring Patterns
  </div>
  <table>
    <tr>
      <th>Day</th><th>Time</th><th>Broker</th>
      <th>Pickup</th><th>Frequency</th>
    </tr>
"""
        for p in patterns:
            html += f"""
    <tr>
      <td>{p['day_name']}</td>
      <td>{p['pickup_time']}</td>
      <td><b>{p['broker']}</b></td>
      <td>{p['simple_pickup']}</td>
      <td><b>{p['count']}x/week</b></td>
    </tr>"""
        html += "\n  </table>\n</div>"

    if not routes and not historical_routes and not alerts and not extensions and not springfield:
        html += """
<div class="section">
  <div class="empty">
    No dispatch data available yet. Waiting for next pipeline run.
  </div>
</div>"""

    html += "\n</div>\n</body>\n</html>"

    os.makedirs(os.path.dirname(DASHBOARD_OUTPUT), exist_ok=True)
    with open(DASHBOARD_OUTPUT, 'w') as f:
        f.write(html)

    print(f"✅ Dashboard saved to {DASHBOARD_OUTPUT}")
    return DASHBOARD_OUTPUT


if __name__ == "__main__":
    generate_dashboard()
    print("Open: https://joegritter-bit.github.io/nemt-map/dashboard.html")
