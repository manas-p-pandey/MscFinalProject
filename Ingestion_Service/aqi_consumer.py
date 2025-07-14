from kafka import KafkaConsumer
import json
import psycopg2
import os
from datetime import datetime

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

# Create AQI table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS aqi_table (
    id SERIAL PRIMARY KEY,
    site_code TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    measurement_datetime TIMESTAMP NOT NULL,
    aqi INTEGER,
    co DOUBLE PRECISION,
    no DOUBLE PRECISION,
    no2 DOUBLE PRECISION,
    o3 DOUBLE PRECISION,
    so2 DOUBLE PRECISION,
    pm2_5 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    nh3 DOUBLE PRECISION,
    UNIQUE (site_code, measurement_datetime)
);
""")
conn.commit()
print("✅ aqi_table and aqi_data_view checked or created.")

# Kafka consumer
consumer = KafkaConsumer(
    'aqi_data',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='aqi_group'
)

print("✅ AQI consumer started.")

for message in consumer:
    payload = message.value
    site_code = payload.get("site_code")
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    data_records = payload.get("data", [])

    for rec in data_records:
        try:
            measurement_dt = rec.get("measurement_datetime")
            components = rec.get("components", {})

            aqi_value = rec.get("aqi")

            cursor.execute("""
                INSERT INTO aqi_table (
                    site_code, latitude, longitude, measurement_datetime,
                    aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (site_code, measurement_datetime) DO NOTHING;
            """, (
                site_code, lat, lon, measurement_dt,
                aqi_value,
                components.get("co"),
                components.get("no"),
                components.get("no2"),
                components.get("o3"),
                components.get("so2"),
                components.get("pm2_5"),
                components.get("pm10"),
                components.get("nh3")
            ))
            conn.commit()
            print(f"✅ Inserted AQI record for {site_code} at {measurement_dt}")

        except Exception as e:
            print(f"❌ Error inserting AQI data for {site_code} at {measurement_dt}: {e}")
            conn.rollback()
