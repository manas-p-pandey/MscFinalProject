import requests
import psycopg2
from kafka import KafkaProducer
import json
from datetime import datetime, timedelta
import os

def produce_aqi_data():
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

    cursor.execute("""
        SELECT DISTINCT ON (latitude, longitude) latitude, longitude, site_code
        FROM site_table
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        ORDER BY latitude, longitude, date_closed NULLS FIRST;
    """)
    locations = cursor.fetchall()

    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()

    for lat, lon, site_code in locations:
        cursor.execute("""
            SELECT DISTINCT measurement_datetime FROM aqi_table 
            WHERE latitude = %s AND longitude = %s
            ORDER BY measurement_datetime ASC;
        """, (lat, lon))
        existing = set(row[0].replace(minute=0, second=0, microsecond=0) for row in cursor.fetchall())

        expected_hours = []
        current = start_date.replace(minute=0, second=0, microsecond=0)
        while current <= end_date:
            expected_hours.append(current)
            current += timedelta(hours=1)

        missing_hours = [dt for dt in expected_hours if dt not in existing]
        print(f"🔍 AQI: {site_code}, {lat}, {lon} - Missing: {len(missing_hours)} hours")

        for dt in missing_hours:
            # Extra explicit check before API call
            cursor.execute("""
                SELECT 1 FROM aqi_table
                WHERE latitude = %s AND longitude = %s AND measurement_datetime = %s
            """, (lat, lon, dt))
            if cursor.fetchone():
                print(f"⏭️ Skipping existing AQI record for {site_code} at {dt}")
                continue

            start_epoch = int(dt.timestamp())
            end_epoch = start_epoch + 3600

            url = f"http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={start_epoch}&end={end_epoch}&appid={OPENWEATHER_API_KEY}"
            print(f"🌐 Fetching AQI for {site_code} at {dt} | URL: {url}")

            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    data_json = resp.json()
                    records = data_json.get("list", [])
                    if records:
                        payload = {
                            "site_code": site_code,
                            "latitude": lat,
                            "longitude": lon,
                            "data": [
                                {
                                    "measurement_datetime": datetime.utcfromtimestamp(r.get("dt")).strftime("%Y-%m-%d %H:%M:%S"),
                                    "aqi": r.get("main", {}).get("aqi"),
                                    "components": r.get("components", {})
                                }
                                for r in records
                            ]
                        }
                        producer.send("aqi_data", payload)
                        print(f"✅ Sent AQI data for {site_code} at {dt}")
                    else:
                        print(f"⚠️ No AQI data returned for {dt}")

                else:
                    print(f"❌ Error fetching AQI data: HTTP {resp.status_code}")

            except Exception as e:
                print(f"❌ Exception fetching AQI data: {e}")

    producer.flush()
    print("✅ AQI data production completed.")

if __name__ == "__main__":
    produce_aqi_data()
