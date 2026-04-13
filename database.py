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
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    # WAL Mode helps with 'Database Locked' errors
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous = OFF;')
    return conn

def init_db():
    """ Create the tables with a standard schema. """
    conn = get_connection()
    cursor = conn.cursor()
    
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
    """ Adds new columns to DB if the dataframe introduces them. """
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
    Save a dataframe of trips safely.
    Fixes:
    1. Deduplicates input (prevents batch crashes).
    2. Uses Fallback Row-by-Row insertion if bulk fails.
    """
    if df.empty:
        return

    # Initialize DB
    init_db() 
    
    # ✅ FIX 1: DEDUPLICATE INPUT
    # If the scraper sends duplicates in the same batch, drop the extras to save the rest.
    initial_len = len(df)
    df = df.drop_duplicates(subset=['trip_id'], keep='last')
    if len(df) < initial_len:
        print(f"   ✂️  Dropped {initial_len - len(df)} duplicate IDs from batch.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df['last_seen'] = now_str
    if 'timestamp' not in df.columns:
        df['timestamp'] = now_str

    max_retries = 3
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_connection()
            align_schema(df, conn)
            cursor = conn.cursor()
            trip_ids = df['trip_id'].tolist()

            # 1. UPDATE "Last Seen" for existing trips
            if trip_ids:
                placeholders = ','.join(['?'] * len(trip_ids))
                sql = f"UPDATE trips SET last_seen = ? WHERE trip_id IN ({placeholders})"
                cursor.execute(sql, [now_str] + trip_ids)
                conn.commit()
            
            # 2. FILTER for purely NEW trips
            existing_check_sql = f"SELECT trip_id FROM trips WHERE trip_id IN ({placeholders})"
            existing_ids = pd.read_sql_query(existing_check_sql, conn, params=trip_ids)['trip_id'].tolist()
            
            new_trips = df[~df['trip_id'].isin(existing_ids)].copy()
            
            if not new_trips.empty:
                # Ensure 'timestamp' is set for new rows
                new_trips['timestamp'] = now_str
                
                # ✅ FIX 2: ROBUST INSERTION
                try:
                    # Try Fast Bulk Insert
                    new_trips.to_sql('trips', conn, if_exists='append', index=False)
                    print(f"   💾 Saved {len(new_trips)} NEW trips. (Updated timestamps for {len(trip_ids)} active trips)")
                except Exception as bulk_e:
                    # If Bulk Fails (e.g. Unique Constraint), try Row-by-Row Fallback
                    print(f"   ⚠️ Bulk Save Failed ({bulk_e}). Switching to Safe Mode...")
                    saved_count = 0
                    for _, row in new_trips.iterrows():
                        try:
                            # Convert single row to DF and save
                            pd.DataFrame([row]).to_sql('trips', conn, if_exists='append', index=False)
                            saved_count += 1
                        except:
                            continue # Skip the bad apple
                    print(f"   ✅ Safe Mode: Saved {saved_count}/{len(new_trips)} trips successfully.")
            else:
                print(f"   🔄 Updated 'last_seen' for {len(trip_ids)} recurring trips.")

            break # Success

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                print(f"   ⚠️ Database Locked (Attempt {attempt+1}). Waiting...")
                time.sleep(2)
            else:
                print(f"   ❌ Database Error: {e}")
                break
        except Exception as e:
            print(f"   ❌ General Save Error: {e}")
            break
        finally:
            if conn: conn.close()

# Initialize on import
init_db()