import json
import os
import psycopg2
from sqlalchemy import create_engine, text
from kafka import KafkaConsumer

# ==========================
# CONFIG
# ==========================
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")

KAFKA_TOPIC = "forecast_data"
FORECAST_TABLE = "forecast_table"

POSTGRES_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
engine = create_engine(POSTGRES_URI)

conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)

# ✅ Only one KafkaConsumer — fix here
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='forecast_consumer_group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# ==========================
# Helper: Create table if not exists
# ==========================
def create_forecast_table():
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {FORECAST_TABLE} (
                id SERIAL PRIMARY KEY,
                site_code TEXT,
                latitude FLOAT,
                longitude FLOAT,
                hour INTEGER,
                day INTEGER,
                month INTEGER,
                weekday INTEGER,
                datetime TIMESTAMP,
                UNIQUE(latitude, longitude, datetime)
            )
        """))

# ==========================
# Helper: Upsert forecast row
# ==========================
def upsert_forecast_row(data):
    with engine.begin() as conn:
        query = text(f"""
            INSERT INTO {FORECAST_TABLE} (site_code, latitude, longitude, hour, day, month, weekday, datetime)
            VALUES (:site_code, :latitude, :longitude, :hour, :day, :month, :weekday, :datetime)
            ON CONFLICT (latitude, longitude, datetime)
            DO UPDATE SET
                site_code = EXCLUDED.site_code,
                hour = EXCLUDED.hour,
                day = EXCLUDED.day,
                month = EXCLUDED.month,
                weekday = EXCLUDED.weekday
        """)
        conn.execute(query, data)

# ==========================
# Main loop
# ==========================
if __name__ == "__main__":
    create_forecast_table()
    print("✅ Listening for forecast data...")

    for message in consumer:
        data = message.value
        upsert_forecast_row(data)
        print(f"✅ Upserted forecast for lat: {data['latitude']}, lon: {data['longitude']}, dt: {data['datetime']}")
