import pandas as pd
import sqlite3
import glob
import os
from datetime import datetime

# CONFIGURATION
DB_PATH = os.path.join('data', 'nemt_data.db')

def backfill_data():
    if not os.path.exists(DB_PATH):
        print("❌ Database not found! Run the bot once first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print("🔌 Connected to database...")

    # 1. Get list of existing Trip IDs so we don't duplicate
    try:
        existing_ids = pd.read_sql_query("SELECT trip_id FROM trips", conn)['trip_id'].tolist()
        existing_ids = set(existing_ids) # Make it a set for fast checking
        print(f"📊 Database currently has {len(existing_ids)} trips.")
    except Exception as e:
        print(f"⚠️ Could not read existing trips: {e}")
        existing_ids = set()

    # 2. Find CSV files
    csv_files = glob.glob("mtm_trips_*.csv")
    csv_files.sort() # Process in order
    print(f"📂 Found {len(csv_files)} CSV files to process.")

    total_added = 0

    for file in csv_files:
        try:
            # Read CSV
            df = pd.read_csv(file)
            
            # STANDARDISATION: Rename columns if they don't match DB exactly
            # (Adjust these keys if your CSV headers are different!)
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # timestamp logic
            if 'timestamp' not in df.columns:
                try:
                    # Extract time from filename: mtm_trips_20260122_2303.csv
                    parts = file.split('_')
                    time_str = parts[2] + "_" + parts[3].replace('.csv', '')
                    dt = datetime.strptime(time_str, "%Y%m%d_%H%M")
                    df['timestamp'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # FILTER: Only keep trips that aren't in the DB yet
            original_count = len(df)
            df = df[~df['trip_id'].isin(existing_ids)]
            new_count = len(df)

            if new_count > 0:
                # Append only the new stuff
                df.to_sql('trips', conn, if_exists='append', index=False)
                total_added += new_count
                
                # Update our local list of IDs so we don't add them again from the next file
                existing_ids.update(df['trip_id'].tolist())
                print(f"   ✅ {file}: Added {new_count} new trips (Skipped {original_count - new_count} duplicates)")
            else:
                print(f"   zzz {file}: All {original_count} trips already exist.")

        except Exception as e:
            # THIS TIME: Print the actual error!
            print(f"   ❌ ERROR in {file}: {e}")

    conn.close()
    print("-" * 30)
    print(f"🎉 DONE: Successfully added {total_added} new records.")

if __name__ == "__main__":
    backfill_data()