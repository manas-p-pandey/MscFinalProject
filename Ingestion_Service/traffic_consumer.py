import json
from kafka import KafkaConsumer
import psycopg2

# Config
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
POSTGRES_HOST = "db"
POSTGRES_DB = "mscds"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "Admin123"

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS traffic_table (
    id SERIAL PRIMARY KEY,
    measurement_datetime TIMESTAMP,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    traffic_flow TEXT,
    traffic_density TEXT,
    UNIQUE (measurement_datetime, latitude, longitude)
);
""")
conn.commit()
print("✅ synthetic_traffic_data table checked or created.")

# Create or replace daily aggregation view
cursor.execute("""
CREATE OR REPLACE VIEW public.historical_data_view
 AS
 SELECT DISTINCT ON (s.site_code, s.latitude, s.longitude, a.measurement_datetime) s.site_code,
    s.site_name,
    s.site_type,
    s.latitude,
    s.longitude,
    a.measurement_datetime AS datetime,
    EXTRACT(isodow FROM a.measurement_datetime)::integer AS day_of_week,
    a.aqi,
    a.co,
    a.no,
    a.no2,
    a.o3,
    a.so2,
    a.pm2_5,
    a.pm10,
    a.nh3,
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
    t.traffic_flow,
    t.traffic_density
   FROM aqi_table a
     JOIN weather_table w ON a.measurement_datetime = w."timestamp" AND a.latitude = w.latitude AND a.longitude = w.longitude
     JOIN traffic_table t ON a.measurement_datetime = t.measurement_datetime AND a.latitude = t.latitude AND a.longitude = t.longitude
     JOIN site_table s ON a.latitude = s.latitude AND a.longitude = s.longitude
  ORDER BY s.site_code, s.latitude, s.longitude, a.measurement_datetime, a.id DESC, w.id DESC, t.id DESC;

ALTER TABLE public.historical_data_view
    OWNER TO postgres;
""")
conn.commit()
print("✅ View synthetic_traffic_daily_view created or replaced.")

# Setup Kafka consumer
consumer = KafkaConsumer(
    "traffic_data",
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    auto_offset_reset="earliest",
)

def run():
    print("✅ Consumer started, waiting for messages...")

    for message in consumer:
        data = message.value
        try:
            cursor.execute("""
            INSERT INTO traffic_table (
            measurement_datetime, latitude, longitude,
            traffic_flow, traffic_density
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (measurement_datetime, latitude, longitude) DO NOTHING;
            """, (
            data["measurement_datetime"],
            data["latitude"],
            data["longitude"],
            data["traffic_flow"],
            data["traffic_density"]
            ))
            conn.commit()
            print(f"✅ Inserted (or skipped duplicate): datetime={data['measurement_datetime']}, flow={data['traffic_flow']}, density={data['traffic_density']}")

        except Exception as e:
            print(f"❌ Error inserting synthetic traffic data: {e}")
            conn.rollback()