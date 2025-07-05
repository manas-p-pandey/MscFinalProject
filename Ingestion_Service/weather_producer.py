import requests
import psycopg2
from kafka import KafkaProducer
import json
import time
from datetime import datetime, timedelta
import os

# Config
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "0fb0f50c2badb10762006b6384c5b5da")

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)
cursor = conn.cursor()

# Setup weather Kafka producer topic
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Fetch locations
cursor.execute("SELECT DISTINCT latitude, longitude FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
locations = cursor.fetchall()

# For each location
for lat, lon in locations:
    print(f"🔄 Processing weather for lat: {lat}, lon: {lon}")

    # From 30 days ago up to now
    for days_ago in range(365, -4, -1):
        dt = datetime.now() - timedelta(days=days_ago)
        for hour in range(0, 24):
            target_time = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Check if record exists
            cursor.execute(
                "SELECT 1 FROM weather_table WHERE latitude = %s AND longitude = %s AND timestamp = %s",
                (lat, lon, target_time)
            )
            if cursor.fetchone():
                print(f"⏭️ Skipping (already exists): {target_time}")
                continue  # Skip to next hour

            epoch_time = int(target_time.timestamp())
            url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={epoch_time}&appid={OPENWEATHER_API_KEY}"
            print(f"🌐 URL: {url}")

            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    data_json = resp.json()
                    hourly_data = data_json.get("data", [])

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
    time.sleep(3600)
