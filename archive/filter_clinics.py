import csv
import glob
import os

def load_clinic_list(filename="clinics.txt"):
    """Reads the text file and returns a list of search terms."""
    if not os.path.exists(filename):
        print(f"⚠️ Warning: '{filename}' not found. Please create it!")
        return []
    
    with open(filename, "r") as f:
        # Filter out comments and empty lines
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    print(f"📋 Loaded {len(lines)} clinic locations from {filename}")
    return lines

def filter_trips():
    # 1. Load the Watchlist
    target_clinics = load_clinic_list()
    if not target_clinics:
        return

    # 2. Find the most recent MTM trip file
    list_of_files = glob.glob('mtm_trips_*.csv') 
    if not list_of_files:
        print("❌ No 'mtm_trips' CSV file found! Please run the scraper first.")
        return
        
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"📂 Reading trips from: {latest_file}")

    matched_trips = []
    
    # 3. Scan the file
    try:
        with open(latest_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Get the addresses from the CSV
                pickup = row.get("Pickup", "").lower()
                dropoff = row.get("Dropoff", "").lower()
                
                is_match = False
                matched_name = ""
                
                for target in target_clinics:
                    # We verify if the specific address snippet is in the trip
                    if target.lower() in pickup or target.lower() in dropoff:
                        is_match = True
                        matched_name = target
                        break
                
                if is_match:
                    row["Matched_Clinic"] = matched_name
                    matched_trips.append(row)

    except Exception as e:
        print(f"⚠️ Error reading file: {e}")
        return

    # 4. Save the VIP List
    if matched_trips:
        output_filename = "priority_clinic_trips.csv"
        
        fieldnames = list(matched_trips[0].keys())
        
        with open(output_filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matched_trips)
            
        print("\n" + "="*60)
        print(f"✅ SUCCESS! Found {len(matched_trips)} matching trips.")
        print(f"📄 Saved to: {output_filename}")
        print("="*60)
        
        for trip in matched_trips[:5]:
             print(f"   🚑 {trip['Date']} | ${trip['Price']} | Match: {trip['Matched_Clinic']}")
    else:
        print("\n❌ No matching trips found. (Try adding more keywords to clinics.txt)")

if __name__ == "__main__":
    filter_trips()