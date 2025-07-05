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
    measurement_datetime TIMESTAMP NOT NULL,
    nitric_oxide DOUBLE PRECISION,
    nitrogen_dioxide DOUBLE PRECISION,
    oxides_of_nitrogen DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    pm25 DOUBLE PRECISION,
    UNIQUE (site_code, measurement_datetime)
);
""")

cursor.execute("""
CREATE OR REPLACE VIEW public.aqi_data_view
 AS
 SELECT DISTINCT aqi.id,
    aqi.site_code,
    site.site_name,
    site.site_type,
    site.local_authority_name,
    site.latitude,
    site.longitude,
    site.date_opened,
    site.date_closed,
    site.site_link,
    aqi.measurement_datetime,
    aqi.nitric_oxide,
    aqi.nitrogen_dioxide,
    aqi.oxides_of_nitrogen,
    aqi.pm10,
    aqi.pm25
   FROM aqi_table aqi
     JOIN site_table site ON aqi.site_code = site.site_code
  ORDER BY aqi.measurement_datetime DESC;

ALTER VIEW public.aqi_data_view
    OWNER TO postgres;
""")
conn.commit()
print("✅ aqi_table checked or created.")

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
    data_records = payload.get("data", [])

    for rec in data_records:
        try:
            measurement_dt = rec["@MeasurementDateGMT"]

            insert_dict = {
                "nitric_oxide": float(rec.get("@Data1")) if rec.get("@Data1") not in (None, "", " ") else None,
                "nitrogen_dioxide": float(rec.get("@Data2")) if rec.get("@Data2") not in (None, "", " ") else None,
                "oxides_of_nitrogen": float(rec.get("@Data3")) if rec.get("@Data3") not in (None, "", " ") else None,
                "pm10": float(rec.get("@Data4")) if rec.get("@Data4") not in (None, "", " ") else None,
                "pm25": float(rec.get("@Data5")) if rec.get("@Data5") not in (None, "", " ") else None
            }

            if all(v is None for v in insert_dict.values()):
                continue

            columns_str = ", ".join(insert_dict.keys())
            placeholders_str = ", ".join(['%s'] * len(insert_dict))

            sql = f"""
                INSERT INTO aqi_table (
                    site_code, measurement_datetime, {columns_str}
                ) VALUES (
                    %s, %s, {placeholders_str}
                )
                ON CONFLICT (site_code, measurement_datetime) DO NOTHING;
            """

            cursor.execute(sql, (
                site_code,
                measurement_dt,
                *insert_dict.values()
            ))
            conn.commit()
            print(f"✅ Inserted AQI record for {site_code} at {measurement_dt}")

        except Exception as e:
            print(f"❌ Error inserting AQI data for {site_code} at {measurement_dt}: {e}")
            conn.rollback()
