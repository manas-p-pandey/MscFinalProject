from kafka import KafkaConsumer
import json
import psycopg2
import os
from datetime import datetime
from zoneinfo import ZoneInfo

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

# Create weather_table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS weather_table (
    id SERIAL PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    timestamp TIMESTAMP WITH TIME ZONE,
    temp DOUBLE PRECISION,
    feels_like DOUBLE PRECISION,
    pressure INTEGER,
    humidity INTEGER,
    dew_point DOUBLE PRECISION,
    uvi DOUBLE PRECISION,
    clouds INTEGER,
    visibility INTEGER,
    wind_speed DOUBLE PRECISION,
    wind_deg INTEGER,
    weather_main TEXT,
    weather_description TEXT,
    UNIQUE (latitude, longitude, timestamp)
);
""")
cursor.execute("""
CREATE OR REPLACE VIEW weather_data_view AS
SELECT
    w.id,
    w.latitude,
    w.longitude,
    -- Convert timestamp with time zone to local datetime without offset
    (w.timestamp AT TIME ZONE 'Europe/London')::timestamp AS local_datetime,
    w.temp,
    w.feels_like,
    w.pressure,
    w.humidity,
    w.dew_point,
    w.uvi,
    w.clouds,
    w.visibility,
    w.wind_speed,
    w.wind_deg,
    w.weather_main,
    w.weather_description,
    s.site_code,
    s.site_name,
    s.site_type,
    s.local_authority_name,
    s.latitudeWGS84,
    s.longitudeWGS84,
    s.date_opened,
    s.date_closed,
    s.site_link
FROM
    weather_table w
JOIN
    site_table s
ON
    w.latitude = s.latitude
    AND w.longitude = s.longitude;

ALTER TABLE public.weather_data_view
    OWNER TO postgres;

""")
conn.commit()
print("✅ weather_table checked or created.")

# Existing AQI consumer remains unchanged (if present) --------------------------------------

# Consumer for weather data
weather_consumer = KafkaConsumer(
    'weather_data',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='weather_group'
)

print("✅ Weather consumer started.")

for message in weather_consumer:
    payload = message.value
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    rec = payload.get("record", {})

    try:
        # Convert epoch to local datetime
        dt_epoch = rec.get("dt")
        if dt_epoch:
            dt_utc = datetime.utcfromtimestamp(dt_epoch)
            dt_local = dt_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Europe/London"))
        else:
            dt_local = None

        weather_main = rec.get("weather", [{}])[0].get("main") if rec.get("weather") else None
        weather_desc = rec.get("weather", [{}])[0].get("description") if rec.get("weather") else None

        cursor.execute("""
            INSERT INTO weather_table (
                latitude, longitude, timestamp, temp, feels_like, pressure, humidity, dew_point,
                uvi, clouds, visibility, wind_speed, wind_deg, weather_main, weather_description
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (latitude, longitude, timestamp) DO NOTHING;
        """, (
            lat,
            lon,
            dt_local,
            rec.get("temp"),
            rec.get("feels_like"),
            rec.get("pressure"),
            rec.get("humidity"),
            rec.get("dew_point"),
            rec.get("uvi"),
            rec.get("clouds"),
            rec.get("visibility"),
            rec.get("wind_speed"),
            rec.get("wind_deg"),
            weather_main,
            weather_desc
        ))
        conn.commit()
        print(f"✅ Inserted weather record for ({lat}, {lon}) at {dt_local}")

    except Exception as e:
        print(f"❌ Error inserting weather data for ({lat}, {lon}): {e}")
        conn.rollback()
