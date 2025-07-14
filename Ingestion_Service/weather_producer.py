import requests
import psycopg2
from kafka import KafkaProducer
import json
from datetime import datetime
import os

def produce_weather_data():
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "0fb0f50c2badb10762006b6384c5b5da")

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cursor = conn.cursor()

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    # Get missing records using left join
    cursor.execute("""
        SELECT DISTINCT a.measurement_datetime, a.latitude, a.longitude, s.site_code
        FROM aqi_table a
        JOIN site_table s
          ON a.latitude = s.latitude AND a.longitude = s.longitude
        LEFT JOIN weather_table w
          ON a.measurement_datetime = w.timestamp
         AND a.latitude = w.latitude
         AND a.longitude = w.longitude
        WHERE w.timestamp IS NULL
        ORDER BY a.measurement_datetime, a.latitude, a.longitude desc;
    """)
    missing_records = cursor.fetchall()
    print(f"🔍 Total missing weather records to process: {len(missing_records)}")

    for dt, lat, lon, site_code in missing_records:
        # Extra explicit check in weather_table before API call
        cursor.execute("""
            SELECT 1 FROM weather_table
            WHERE latitude = %s AND longitude = %s AND timestamp = %s
        """, (lat, lon, dt))
        if cursor.fetchone():
            print(f"⏭️ Skipping existing weather record for {site_code} at {dt}")
            continue

        epoch_time = int(dt.timestamp())
        url = f"https://api.openweathermap.org/data/3.0/onecall/timemachine?lat={lat}&lon={lon}&dt={epoch_time}&appid={OPENWEATHER_API_KEY}"
        print(f"🌐 Fetching weather for {site_code} at {dt} | URL: {url}")

        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data_json = resp.json()
                hourly_data = data_json.get("hourly") or data_json.get("data", [])

                if hourly_data:
                    for weather_rec in hourly_data:
                        payload = {
                            "latitude": lat,
                            "longitude": lon,
                            "site_code": site_code,
                            "record": weather_rec
                        }
                        producer.send("weather_data", payload)
                    print(f"✅ Sent weather data for {site_code} at {dt}")
                else:
                    print(f"⚠️ No weather data returned for {dt}")

            else:
                print(f"❌ Error fetching weather data: HTTP {resp.status_code}")

        except Exception as e:
            print(f"❌ Exception fetching weather data: {e}")

    producer.flush()
    print("✅ Weather data production completed.")

if __name__ == "__main__":
    produce_weather_data()
