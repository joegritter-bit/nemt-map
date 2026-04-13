
import pandas as pd
from datetime import timedelta

def create_driver_schedule():
    """
    Transforms the daily_schedule.csv into the driver_schedule.csv format
    required by the stitch_route.py script.
    """
    daily_schedule_df = pd.read_csv("daily_schedule.csv")

    # Create the driver_schedule.csv file with the required format
    with open("driver_schedule.csv", "w", newline="") as f:
        f.write("Driver,Date,Pick up time,Drop off time,PU Address,DO Address,Mileage\n")
        for _, row in daily_schedule_df.iterrows():
            # Estimate drop off time (assuming 30 minutes per trip for now)
            pickup_time = pd.to_datetime(row["Time"], format="%H%M")
            dropoff_time = pickup_time + timedelta(minutes=30)

            # Estimate mileage (using a placeholder value for now)
            mileage = 10.0

            f.write(f"{row['Driver Name']},{row['Appointment Date']},{pickup_time.strftime('%H:%M')},{dropoff_time.strftime('%H:%M')},\"{row['Pickup Address']}, {row['Pickup City']}, {row['Pickup State']} {row['Pickup Zip Code']}\",\"{row['Delivery Address']}, {row['Delivery City']}, {row['Delivery State']} {row['Delivery Zip Code']}\",{mileage}\n")
    print("driver_schedule.csv created successfully.")

if __name__ == "__main__":
    create_driver_schedule()
