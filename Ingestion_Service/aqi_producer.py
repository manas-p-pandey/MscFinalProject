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

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Get distinct lat/lon and site_code
cursor.execute("SELECT DISTINCT latitude, longitude, site_code FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
locations = cursor.fetchall()
print("✅ Sites fetched:", len(locations))

while True:
    for lat, lon, site_code in locations:
        for day_offset in range(0, 366):
            target_date = datetime.now() - timedelta(days=day_offset)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            start_epoch = int(start_of_day.timestamp())
            end_epoch = int(end_of_day.timestamp())

            url = f"http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={start_epoch}&end={end_epoch}&appid={OPENWEATHER_API_KEY}"
            print(f"🔄 Fetching AQI for {site_code}: {target_date.strftime('%Y-%m-%d')} | URL: {url}")

            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    data_json = resp.json()
                    records = data_json.get("list", [])

                    records_to_send = []

                    for rec in records:
                        dt_epoch = rec.get("dt")
                        if not dt_epoch:
                            continue

                        measurement_dt = datetime.utcfromtimestamp(dt_epoch).strftime("%Y-%m-%d %H:%M:%S")
                        main_json = rec.get("main",{})
                        aqi = main_json.get("aqi")
                        cursor.execute("""
                            SELECT 1 FROM aqi_table
                            WHERE site_code = %s AND measurement_datetime = %s
                        """, (site_code, measurement_dt))
                        if cursor.fetchone():
                            print(f"⏭️ Skipping existing AQI record for {site_code} at {measurement_dt}")
                            continue

                        records_to_send.append({
                            "measurement_datetime": measurement_dt,
                            "aqi":aqi,
                            "components": rec.get("components", {})
                        })

                    if records_to_send:
                        payload = {
                            "site_code": site_code,
                            "latitude": lat,
                            "longitude": lon,
                            "data": records_to_send
                        }
                        producer.send("aqi_data", payload)
                        print(f"✅ Sent {len(records_to_send)} new AQI records for {site_code} on {target_date.strftime('%Y-%m-%d')}")
                    else:
                        print(f"⚠️ No new AQI records to send for {site_code} on {target_date.strftime('%Y-%m-%d')}")

                else:
                    print(f"❌ Error fetching AQI data: HTTP {resp.status_code}")

            except Exception as e:
                print(f"❌ Exception fetching AQI data for {site_code} on {target_date.strftime('%Y-%m-%d')}: {e}")

    producer.flush()
    time.sleep(3600)
