import time
from datetime import datetime, timedelta

from site_producer import produce_site_data
from aqi_producer import produce_aqi_data
from weather_producer import produce_weather_data
from traffic_producer import produce_traffic_data
from forecast_producer import produce_forecast_data


def main():
    print(f"🚀 Starting main producer pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Call site producer
    produce_site_data()
    time.sleep(5)
    # Call AQI producer
    produce_aqi_data()
    time.sleep(5)
    # Call weather producer
    produce_weather_data()
    time.sleep(5)
    # Call traffic producer
    produce_traffic_data()
    time.sleep(5)
    # Call forecast producer
    produce_forecast_data()

    print(f"✅ All producers completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    # logic to wait and call at every hour of the day if not already running
    main()
    firstRun = datetime.now()
    print(f"⏰ Waiting to start next batch at {firstRun.replace(hour=1, minute=0, second=0, microsecond=0)+timedelta(days=1)}")
    while True:
        now = datetime.now()+timedelta(hours=+1) # to get local time from utc
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second

        # Check if it's the start of a new hour and hasn't been run in this hour
        if current_minute == 0 and current_second>=0 and current_second < 10 and current_hour ==1:
            main()
            print(f"⏰ Waiting to start next batch at {now.replace(hour=1, minute=0, second=0, microsecond=0)+timedelta(days=1)}")
        # Sleep briefly to reduce CPU load
        time.sleep(1)
