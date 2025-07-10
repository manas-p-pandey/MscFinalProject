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
CREATE OR REPLACE VIEW public.traffic_data_view AS
SELECT
    DATE(t.measurement_datetime) AS day,
    t.latitude,
    t.longitude,
    s.site_code,
    s.site_name,
    s.site_type,
    mode() WITHIN GROUP (ORDER BY t.traffic_flow) AS daily_traffic_flow,
    mode() WITHIN GROUP (ORDER BY t.traffic_density) AS daily_traffic_density
FROM traffic_table t
LEFT JOIN site_table s
ON t.latitude = s.latitude AND t.longitude = s.longitude
GROUP BY day, t.latitude, t.longitude, s.site_code, s.site_name, s.site_type
ORDER BY day DESC;
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

print("✅ Consumer started, waiting for messages...")

for message in consumer:
    data = message.value

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


