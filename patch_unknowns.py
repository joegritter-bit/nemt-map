import sqlite3
import os

DB_PATH = 'data/nemt_data.db'

def patch_database():
    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Exact Match Updates
    exact_updates = [
        ("Williamson County", "1036 Rolling Acres Dr Marion 62959"),
        ("Menard County", "14405 Wilson Rd, , Athens Il, 62613"),
        ("Kankakee County", "1047 S Washington Ave, , Kankakee Il, 60901")
    ]

    # Partial Match Updates (wildcards for truncated/apt addresses)
    partial_updates = [
        ("Cook County", "7205 S Yates Blvd%"),
        ("Rock Island County", "1073 50th Ave%")
    ]

    print("🔧 Patching Geo Cache Round 7...")
    count = 0

    # Apply Exact Matches
    for county, address in exact_updates:
        cursor.execute("UPDATE geo_cache SET county = ? WHERE address = ?", (county, address))
        if cursor.rowcount > 0:
            print(f"✅ Fixed: {address[:30]}... -> {county}")
            count += 1
        else:
            print(f"⚠️ Not found (exact): {address[:30]}...")

    # Apply Partial Matches
    for county, partial_addr in partial_updates:
        cursor.execute("UPDATE geo_cache SET county = ? WHERE address LIKE ?", (county, partial_addr))
        if cursor.rowcount > 0:
            print(f"✅ Fixed (Wildcard): {partial_addr[:30]}... -> {county}")
            count += cursor.rowcount 
        else:
            print(f"⚠️ Not found (wildcard): {partial_addr[:30]}...")

    conn.commit()
    conn.close()
    print(f"\n🎉 Successfully patched {count} addresses.")
    print("Run 'python market_intel.py' again to see the impact!")

if __name__ == "__main__":
    patch_database()