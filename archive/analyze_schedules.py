
import csv
from collections import defaultdict
from datetime import datetime, timedelta

def analyze_schedules():
    """
    Analyzes the trip data to reconstruct driver schedules and saves it to a CSV file.
    """
    schedules = defaultdict(lambda: defaultdict(list))
    filename = "1.01.26 to 3.17.26 trips data.xlsx - Export Trip.csv"

    with open(filename, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Trip Status'] == 'VALID':
                driver = row['Driver Name']
                day = row['Appointment Day of Week']
                time_str = row['Time']
                if driver and time_str:
                    schedules[driver][day].append(time_str)

    output_filename = "master_schedule.csv"
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Driver Name', 'Day of Week', 'Start Time', 'End Time', 'Total Hours']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for driver, schedule in schedules.items():
            for day, times in schedule.items():
                if not times:
                    continue

                # Convert times to datetime objects for sorting
                time_objects = [datetime.strptime(t, '%H%M') for t in times]
                start_time = min(time_objects)
                end_time = max(time_objects)
                
                # Calculate total hours
                duration = end_time - start_time
                total_hours = round(duration.total_seconds() / 3600, 2)

                writer.writerow({
                    'Driver Name': driver,
                    'Day of Week': day,
                    'Start Time': start_time.strftime('%H:%M'),
                    'End Time': end_time.strftime('%H:%M'),
                    'Total Hours': total_hours
                })
    
    print(f"Master schedule has been generated and saved to {output_filename}")

if __name__ == "__main__":
    analyze_schedules()
