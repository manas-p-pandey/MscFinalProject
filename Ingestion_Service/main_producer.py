import time
from datetime import datetime

from site_producer import produce_site_data
from aqi_producer import produce_aqi_data
from weather_producer import produce_weather_data
from traffic_producer import produce_traffic_data

def main():
    print(f"🚀 Starting main producer pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Call site producer
    produce_site_data()

    # Call AQI producer
    produce_aqi_data()

    # Call weather producer
    produce_weather_data()

    # Call traffic producer
    produce_traffic_data()

    print(f"✅ All producers completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    last_run_hour = None
    # first run when producer starts
    main()
    # logic to wait and call at every hour of the day if not already running
    while True:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second

        # Check if it's the start of a new hour and hasn't been run in this hour
        if current_minute == 0 and current_second < 10 and current_hour != last_run_hour:
            main()
            last_run_hour = current_hour
            print("⏰ Completed run for this hour. Waiting for next hour...")

        # Sleep briefly to reduce CPU load
        time.sleep(5)
