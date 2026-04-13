
import csv
from collections import defaultdict

def generate_daily_schedule():
    """
    Analyzes the trip data to create a detailed daily schedule for each driver,
    including pickup and delivery locations.
    """
    schedules = defaultdict(list)
    filename = "1.01.26 to 3.17.26 trips data.xlsx - Export Trip.csv"

    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Trip Status'] == 'VALID':
                driver = row['Driver Name']
                if driver:
                    schedules[driver].append(row)

    output_filename = "daily_schedule.csv"
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Driver Name', 'Appointment Date', 'Appointment Day of Week', 'Time',
            'Pickup Address', 'Pickup City', 'Pickup State', 'Pickup Zip Code',
            'Delivery Address', 'Delivery City', 'Delivery State', 'Delivery Zip Code',
            'Trip Status'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for driver, trips in schedules.items():
            # Sort trips by date and time
            sorted_trips = sorted(trips, key=lambda x: (x['Appointment Date'], x['Time']))
            for trip in sorted_trips:
                writer.writerow({
                    'Driver Name': driver,
                    'Appointment Date': trip['Appointment Date'],
                    'Appointment Day of Week': trip['Appointment Day of Week'],
                    'Time': trip['Time'],
                    'Pickup Address': trip['Pickup Address'],
                    'Pickup City': trip['Pickup City'],
                    'Pickup State': trip['Pickup State'],
                    'Pickup Zip Code': trip['Pickup Zip Code'],
                    'Delivery Address': trip['Delivery Address'],
                    'Delivery City': trip['Delivery City'],
                    'Delivery State': trip['Delivery State'],
                    'Delivery Zip Code': trip['Delivery Zip Code'],
                    'Trip Status': trip['Trip Status']
                })
    
    print(f"Daily schedule has been generated and saved to {output_filename}")

if __name__ == "__main__":
    generate_daily_schedule()
