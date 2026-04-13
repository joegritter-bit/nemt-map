import pandas as pd
import os

# Update this to exactly match your downloaded file name
FILE_NAME = "routegenie.csv"
OUTPUT_FILE = "proposed_clinics.csv"

# Keywords used to identify Substance Abuse / Methadone clinics
SA_KEYWORDS = [
    'recovery', 'medmark', 'treatment', 'rehab', 'methadone', 
    'suboxone', 'addiction', 'behavioral', 'symetria', 'crossroads'
]

def generate_clinic_report():
    if not os.path.exists(FILE_NAME):
        print(f"❌ File not found: {FILE_NAME}")
        return

    print("📊 Processing RouteGenie Trip History...")
    
    # Load the CSV
    df = pd.read_csv(FILE_NAME, low_memory=False)
    
    # We only care about Drop Offs to identify clinics
    df_do = df[['DO Facility', 'DO Address']].dropna(subset=['DO Address']).copy()
    
    # Clean up the data
    df_do['DO Facility'] = df_do['DO Facility'].fillna('Unknown Facility').str.strip()
    df_do['DO Address'] = df_do['DO Address'].str.strip()
    
    # Group by Facility and Address, count frequencies
    clinic_counts = df_do.groupby(['DO Facility', 'DO Address']).size().reset_index(name='Total_Trips')
    
    # Sort highest frequency first
    clinic_counts = clinic_counts.sort_values(by='Total_Trips', ascending=False)

    # Function to flag Substance Abuse clinics
    def check_substance_abuse(facility_name):
        name_lower = str(facility_name).lower()
        for keyword in SA_KEYWORDS:
            if keyword in name_lower:
                return "Yes"
        return "No"

    # Apply the cross-reference check
    clinic_counts['Is_Substance_Abuse'] = clinic_counts['DO Facility'].apply(check_substance_abuse)
    
    # Save the final report
    clinic_counts.to_csv(OUTPUT_FILE, index=False)
    
    print("\n✅ Analysis Complete!")
    print(f"💾 Saved frequency report to: {OUTPUT_FILE}")
    print("\nTop 5 Most Frequented Drop-Offs:")
    print(clinic_counts.head(5).to_string(index=False))

if __name__ == "__main__":
    generate_clinic_report()