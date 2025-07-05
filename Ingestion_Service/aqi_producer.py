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

# Get site codes from existing site_table
cursor.execute("SELECT site_code FROM site_table;")
site_codes = [row[0] for row in cursor.fetchall()]
print("✅ Site codes fetched:", site_codes)

# Main loop
while True:
    for site_code in site_codes:
        # Always go back 365 days by default
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://api.erg.ic.ac.uk/AirQuality/Data/Wide/Site/SiteCode={site_code}/StartDate={start_date}/EndDate={end_date}/Json"

        print(f"🔄 Fetching: {url}")

        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data_json = resp.json()
                records = data_json.get("AirQualityData", {}).get("RawAQData", {}).get("Data", [])

                # Check each record before adding
                records_to_send = []
                for rec in records:
                    dt_str = rec.get("@MeasurementDateGMT")
                    if not dt_str:
                        continue

                    # Check if at least one data field has value
                    has_value = any(rec.get(f"@Data{i}") not in (None, "", " ") for i in range(1, 6))
                    if not has_value:
                        continue

                    # Check if record already exists
                    cursor.execute("""
                        SELECT 1 FROM aqi_table
                        WHERE site_code = %s AND measurement_datetime = %s
                    """, (site_code, dt_str))
                    if cursor.fetchone():
                        print(f"⏭️ Skipping existing record for {site_code} at {dt_str}")
                        continue

                    # Add to list if not found
                    records_to_send.append(rec)

                if records_to_send:
                    payload = {
                        "site_code": site_code,
                        "data": records_to_send
                    }
                    producer.send("aqi_data", payload)
                    print(f"✅ Sent {len(records_to_send)} new records to Kafka for {site_code}")
                else:
                    print(f"⚠️ No new records to send for {site_code}")

            else:
                print(f"❌ Error fetching data: HTTP {resp.status_code}")

        except Exception as e:
            print(f"❌ Exception fetching data for {site_code}: {e}")

    producer.flush()
    time.sleep(3600)
