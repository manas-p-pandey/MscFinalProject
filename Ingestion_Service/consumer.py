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

consumer = KafkaConsumer(
    'aqi_data',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='aqi_group'
)

print("✅ Consumer started.")

for message in consumer:
    payload = message.value
    site_code = payload.get("site_code")
    data_records = payload.get("data", [])

    # Skip if no data
    if not data_records:
        continue

    # Get columns definition from first record
    # We'll assume columns mapping remains the same in this batch
    columns_list = payload.get("columns", [])  # You can attach this if needed in producer, or parse from API response

    # Example: you might pass full Columns section in payload, here parsing dynamically
    # Instead, we parse again here
    if "Columns" in payload:
        columns_section = payload["Columns"]
    else:
        columns_section = data_records[0].get("Columns")

    # Parse columns
    if columns_section and "Column" in columns_section:
        column_map = {}
        for col in columns_section["Column"]:
            col_id = col["@ColumnId"]
            col_name_raw = col["@ColumnName"]
            pollutant_name = col_name_raw.split(":")[1].strip().split(" ")[0].lower()
            pollutant_name = pollutant_name.replace(".", "").replace("(", "").replace(")", "").replace("/", "_").replace("-", "_")
            pollutant_name = pollutant_name.replace(" ", "_")
            column_map[col_id] = pollutant_name
    else:
        # Fallback: default mapping for Data1 to Data5
        column_map = {
            "Data1": "nitric_oxide",
            "Data2": "nitrogen_dioxide",
            "Data3": "oxides_of_nitrogen",
            "Data4": "pm10",
            "Data5": "pm25"
        }

    for rec in data_records:
        try:
            measurement_dt = rec["@MeasurementDateGMT"]

            # Build insert_dict dynamically as before
            insert_dict = {}
            for data_key, col_name in column_map.items():
                value = rec.get(f"@{data_key}")
                insert_dict[col_name] = float(value) if value not in (None, "", " ") else None

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
            print(f"✅ Inserted record for {site_code} at {measurement_dt}")

        except Exception as e:
            print(f"❌ Error inserting data for {site_code} at {measurement_dt}: {e}")
            conn.rollback()
