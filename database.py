import sqlite3
import pandas as pd
import os
from datetime import datetime

# Define the database path
DB_FOLDER = os.path.join(os.getcwd(), 'data')
DB_PATH = os.path.join(DB_FOLDER, 'nemt_data.db')

def get_connection():
    """ Connect to the SQLite database, creating it if needed. """
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    return sqlite3.connect(DB_PATH)

def init_db():
    """ Create the table with a standard schema. """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Core schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            date TEXT,
            pickup_time TEXT,
            miles REAL,
            pickup_address TEXT,
            dropoff_address TEXT,
            broker TEXT,
            timestamp TEXT
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
    # Get current database columns
    cursor.execute("PRAGMA table_info(trips)")
    db_cols = [info[1] for info in cursor.fetchall()]
    
    # Check for missing columns
    for col in df.columns:
        if col not in db_cols:
            print(f"   🔧 Adding new column to database: '{col}'")
            try:
                # Add the column dynamically. 
                # Note: This is simple text substitution; assume safe headers from internal code.
                cursor.execute(f"ALTER TABLE trips ADD COLUMN {col} TEXT")
                conn.commit()
            except Exception as e:
                print(f"   ⚠️ Could not add column {col}: {e}")

def save_batch(df):
    """ Save a dataframe of trips to the database safely. """
    if df.empty:
        return

    init_db() # Ensure basic table exists
    conn = get_connection()
    
    # Add timestamp
    df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. FIX SCHEMA: Make sure DB has all the columns the DF has
    align_schema(df, conn)

    try:
        # 2. FILTER DUPLICATES: Read existing IDs to avoid crashing
        existing_ids = pd.read_sql_query("SELECT trip_id FROM trips", conn)['trip_id'].tolist()
        
        # Keep only trips that are NOT in the database
        new_trips = df[~df['trip_id'].isin(existing_ids)]
        
        if not new_trips.empty:
            new_trips.to_sql('trips', conn, if_exists='append', index=False)
            print(f"   💾 Saved {len(new_trips)} new trips. ({len(df) - len(new_trips)} duplicates skipped)")
        else:
            print("   💤 No new unique trips found in this batch.")

    except Exception as e:
        print(f"   ⚠️ Database Save Error: {e}")
    finally:
        conn.close()