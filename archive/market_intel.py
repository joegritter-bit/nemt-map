import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = 'data/nemt_data.db'

def run_market_deep_dive():
    if not os.path.exists(DB_PATH):
        print("❌ Database not found at " + DB_PATH)
        return

    conn = sqlite3.connect(DB_PATH)
    
    # Join trips with geo_cache and include lat/lon to diagnose failures
    query = """
    SELECT t.trip_id, t.date, t.pickup_time, t.last_seen, t.pickup_address, 
           g.county, g.lat, g.lon
    FROM trips t
    LEFT JOIN geo_cache g ON t.pickup_address = g.address
    """
    df = pd.read_sql_query(query, conn)
    
    # 1. Clean up Time Data
    df['last_seen'] = pd.to_datetime(df['last_seen'], errors='coerce')
    df['hour_added'] = df['last_seen'].dt.hour
    df['day_added'] = df['last_seen'].dt.day_name()
    
    # 2. Normalize "Unknown" counties
    df['county'] = df['county'].fillna('Unknown')
    
    print("=========================================")
    print("       NEMT MARKET INTELLIGENCE v2.0    ")
    print("=========================================\n")

    # --- ANALYSIS 1: WHEN DO NEW TRIPS APPEAR? ---
    df_new_entries = df.sort_values('last_seen').groupby('trip_id').first().reset_index()
    
    print("🕒 TOP 5 TIMES FOR NEW TRIP DROPS")
    print("-----------------------------------------")
    time_stats = df_new_entries.groupby(['day_added', 'hour_added']).size().reset_index(name='count')
    top_times = time_stats.sort_values('count', ascending=False).head(5)
    for _, row in top_times.iterrows():
        print(f"📌 {row['day_added']:<10} at {row['hour_added']:02}:00 — {row['count']} new trips")

    # --- ANALYSIS 2: COUNTY VOLUME ---
    print("\n🗺️ TOP 5 COUNTIES BY TRIP VOLUME")
    print("-----------------------------------------")
    df['trip_date'] = pd.to_datetime(df['date']).dt.date
    county_daily = df.groupby(['trip_date', 'county']).size().reset_index(name='daily_count')
    county_avg = county_daily.groupby('county')['daily_count'].mean().sort_values(ascending=False).head(5)
    
    for county, avg in county_avg.items():
        print(f"📍 {county:<18} — Avg {int(avg)} trips/day")

    # --- ANALYSIS 3: THE "UNKNOWN" FILES ---
    print("\n🕵️ ANALYSIS OF 'UNKNOWN' COUNTIES")
    print("-----------------------------------------")
    unknowns = df[df['county'] == 'Unknown']
    
    if unknowns.empty:
        print("✅ No unknown counties found!")
    else:
        print(f"⚠️ Found {len(unknowns)} trips with Unknown county.\n")
        print("TOP 5 PROBLEM ADDRESSES:")
        
        # Group by address to see the biggest offenders
        problem_addrs = unknowns.groupby(['pickup_address', 'lat', 'lon']).size().reset_index(name='count')
        top_problems = problem_addrs.sort_values('count', ascending=False).head(5)
        
        for _, row in top_problems.iterrows():
            status = "❌ Not Geocoded" if (pd.isna(row['lat']) or row['lat'] == 0) else "✅ Has Coords (Mapping Error)"
            addr_short = row['pickup_address'][:45] + "..." if len(row['pickup_address']) > 45 else row['pickup_address']
            print(f"🔴 {row['count']}x Trips | {status}")
            print(f"   ADDR: {addr_short}")

    conn.close()

if __name__ == "__main__":
    run_market_deep_dive()