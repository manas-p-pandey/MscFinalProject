import requests
import psycopg2
from kafka import KafkaProducer
import json
import time
from datetime import datetime, timedelta
import os

def produce_weather_data():
    # Config
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "8f16726775b3db39aba6f270add66af2")

    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cursor = conn.cursor()

    # Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    # Fetch locations
    cursor.execute("SELECT DISTINCT latitude, longitude FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
    locations = cursor.fetchall()
    print("✅ Sites fetched:", len(locations))

    for lat, lon in locations:
        print(f"🔄 Processing weather for lat: {lat}, lon: {lon}")

        for days_ago in range(365, -1, -1):
            dt = datetime.now() - timedelta(days=days_ago)
            for hour in range(0, 24):
                target_time = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

                # Check if record exists
                cursor.execute(
                    "SELECT 1 FROM weather_table WHERE latitude = %s AND longitude = %s AND timestamp = %s",
                    (lat, lon, target_time)
                )
                if cursor.fetchone():
                    print(f"⏭️ Skipping (already exists): {target_time}, lat:{lat}, lon:{lon}")
                    continue

                epoch_time = int(target_time.timestamp())
                url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={epoch_time}&appid={OPENWEATHER_API_KEY}"
                print(f"🌐 URL: {url}")

                try:
                    resp = requests.get(url)
                    if resp.status_code == 200:
                        data_json = resp.json()
                        hourly_data = data_json.get("hourly", [])

                        if hourly_data:
                            for weather_rec in hourly_data:
                                payload = {
                                    "latitude": lat,
                                    "longitude": lon,
                                    "record": weather_rec
                                }
                                producer.send("weather_data", payload)
                            print(f"✅ Sent weather data for {target_time} (epoch: {epoch_time})")
                        else:
                            print(f"⚠️ No weather data returned for {target_time}")

                    else:
                        print(f"❌ Error fetching weather data: HTTP {resp.status_code}")

                except Exception as e:
                    print(f"❌ Exception fetching weather data: {e}")

    producer.flush()
    print("✅ Weather data production completed.")

# Optional: if run standalone
if __name__ == "__main__":
    produce_weather_data()
    time.sleep(3600)
