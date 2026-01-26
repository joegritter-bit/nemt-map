import sqlite3
import pandas as pd
import os
import time
from datetime import datetime

# Define the database path
DB_FOLDER = os.path.join(os.getcwd(), 'data')
DB_PATH = os.path.join(DB_FOLDER, 'nemt_data.db')

def get_connection():
    """ 
    Connect to the SQLite database with robust settings. 
    - Creates folder if needed.
    - Sets timeout to 30s (waits for locks).
    - Enables WAL Mode (concurrency).
    """
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    
    # Increase timeout to 30 seconds to wait for locks to clear
    conn = sqlite3.connect(DB_PATH, timeout=30)
    
    # ENABLE WAL MODE (The Magic Fix for 'Database Locked' errors)
    # This allows reading and writing at the same time.
    conn.execute('PRAGMA journal_mode=WAL;')
    
    return conn

def init_db():
    """ Create the tables with a standard schema. """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Core Trips Schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            date TEXT,
            pickup_time TEXT,
            miles REAL,
            pickup_address TEXT,
            dropoff_address TEXT,
            broker TEXT,
            timestamp TEXT,
            last_seen TEXT,
            payout REAL
        )
    ''')
    
    # Geo Cache Schema (Crucial for the Map)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geo_cache (
            address TEXT PRIMARY KEY, 
            lat REAL, 
            lon REAL
        )
    ''')
    
    conn.commit()
    conn.close()

def align_schema(df, conn):
    """ 
    Checks if the dataframe has columns that represent NEW fields
    not yet in the database, and adds them automatically.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(trips)")
    db_cols = [info[1] for info in cursor.fetchall()]
    
    for col in df.columns:
        if col not in db_cols:
            print(f"   🔧 Adding new column to database: '{col}'")
            try:
                cursor.execute(f"ALTER TABLE trips ADD COLUMN {col} TEXT")
                conn.commit()
            except Exception as e:
                print(f"   ⚠️ Could not add column {col}: {e}")

def save_batch(df):
    """ 
    Save a dataframe of trips to the database safely.
    Includes RETRY LOGIC to handle database locks.
    """
    if df.empty:
        return

    # Initialize DB (creates tables if missing)
    init_db() 
    
    # Standardize timestamps
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 'last_seen' is NOW for everything in this batch
    df['last_seen'] = now_str
    
    # 'timestamp' (First Seen) is only for new rows, but we set it here for the insert later
    if 'timestamp' not in df.columns:
        df['timestamp'] = now_str

    # RETRY LOGIC (Try 3 times before giving up)
    max_retries = 3
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_connection()
            
            # 1. Ensure Schema matches (Add new columns if found)
            align_schema(df, conn)
            
            cursor = conn.cursor()
            trip_ids = df['trip_id'].tolist()

            # 2. UPDATE "Last Seen" for ALL trips in this batch (Existing + New)
            # This marks old trips as "Still Active"
            if trip_ids:
                placeholders = ','.join(['?'] * len(trip_ids))
                sql = f"UPDATE trips SET last_seen = ? WHERE trip_id IN ({placeholders})"
                cursor.execute(sql, [now_str] + trip_ids)
                conn.commit()
            
            # 3. INSERT New Trips
            # Identify which IDs are already in the DB
            existing_check_sql = f"SELECT trip_id FROM trips WHERE trip_id IN ({placeholders})"
            existing_ids = pd.read_sql_query(existing_check_sql, conn, params=trip_ids)['trip_id'].tolist()
            
            # Filter for trips that are NOT in the DB yet
            new_trips = df[~df['trip_id'].isin(existing_ids)].copy()
            
            if not new_trips.empty:
                # Ensure new trips have the 'timestamp' set to creation time
                new_trips['timestamp'] = now_str
                new_trips.to_sql('trips', conn, if_exists='append', index=False)
                print(f"   💾 Saved {len(new_trips)} NEW trips. (Updated timestamps for {len(trip_ids)} active trips)")
            else:
                print(f"   🔄 Updated 'last_seen' for {len(trip_ids)} recurring trips.")

            # Success! Break the loop
            break

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                print(f"   ⚠️ Database Locked (Attempt {attempt+1}/{max_retries}). Waiting 2s...")
                time.sleep(2)
            else:
                print(f"   ❌ Database Error: {e}")
                break
        except Exception as e:
            print(f"   ⚠️ Database Save Error: {e}")
            break
        finally:
            if conn:
                conn.close()

# Initialize on import to be safe
init_db()