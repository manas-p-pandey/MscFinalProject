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

# Create traffic_table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS traffic_table (
    id SERIAL PRIMARY KEY,
    site_code TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    road_name TEXT,
    closure TEXT,
    directions TEXT,
    severity TEXT,
    category TEXT,
    sub_category TEXT,
    comments TEXT,
    start_datetime TIMESTAMP,
    end_datetime TIMESTAMP,
    distance_km DOUBLE PRECISION,
    UNIQUE (site_code, start_datetime)
);
""")

cursor.execute("""
CREATE OR REPLACE VIEW public.traffic_data_view
 AS
SELECT id, 
    site_code, 
    latitude, 
    longitude,
    road_name, 
    closure,
    directions, 
    severity, 
    category, 
    sub_category, 
    comments,
    start_datetime, 
    end_datetime, 
    distance_km
FROM public.traffic_table
ORDER BY start_datetime, end_datetime DESC;

ALTER VIEW public.traffic_data_view
    OWNER TO postgres;
""")
conn.commit()
print("✅ traffic_table checked or created.")

# Kafka consumer
consumer = KafkaConsumer(
    'traffic_data',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='traffic_group'
)

print("✅ Traffic consumer started.")

for message in consumer:
    payload = message.value

    try:
        site_code = payload.get("site_code")
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        road_name = payload.get("road_name")
        closure = payload.get("closure")
        directions = payload.get("directions")
        severity = payload.get("severity")
        category = payload.get("category")
        sub_category = payload.get("sub_category")
        comments = payload.get("comments")
        start_dt_str = payload.get("start_datetime")
        end_dt_str = payload.get("end_datetime")
        distance_km = payload.get("distance_km")

        # Convert ISO format strings with "Z" to valid Python datetime
        start_dt = datetime.fromisoformat(start_dt_str.replace("Z", "+00:00")) if start_dt_str else None
        end_dt = datetime.fromisoformat(end_dt_str.replace("Z", "+00:00")) if end_dt_str else None

        cursor.execute("""
            INSERT INTO traffic_table (
                site_code, latitude, longitude, road_name, closure, directions,
                severity, category, sub_category, comments, start_datetime,
                end_datetime, distance_km
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (site_code, start_datetime) DO NOTHING;
        """, (
            site_code, latitude, longitude, road_name, closure, directions,
            severity, category, sub_category, comments, start_dt, end_dt, distance_km
        ))
        conn.commit()
        print(f"✅ Inserted traffic data for {site_code} at {start_dt}")

    except Exception as e:
        print(f"❌ Error inserting traffic data: {e}")
        conn.rollback()
