from kafka import KafkaConsumer
import json
import psycopg2
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

# Create site_table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS site_table (
    site_code TEXT PRIMARY KEY,
    site_name TEXT,
    site_type TEXT,
    local_authority_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    latitudeWGS84 DOUBLE PRECISION,
    longitudeWGS84 DOUBLE PRECISION,
    date_opened TIMESTAMP NULL,
    date_closed TIMESTAMP NULL,
    site_link TEXT
);
""")
conn.commit()
print("✅ site_table checked or created.")

# Kafka consumer
consumer = KafkaConsumer(
    'site_data',
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='site_group'
)

print("✅ Site consumer started.")

def remove_duplicates():
    # Delete duplicates keeping one with date_closed IS NULL
    cursor.execute("""
        DELETE FROM site_table st
        USING site_table st2
        WHERE st.site_code <> st2.site_code
          AND st.latitude = st2.latitude
          AND st.longitude = st2.longitude
          AND st2.date_closed IS NULL;
    """)
    conn.commit()
    print("🗑️ Removed duplicate site entries keeping active ones.")

for message in consumer:
    site = message.value

    try:
        cursor.execute("""
            INSERT INTO site_table (
                site_code, site_name, site_type, local_authority_name,
                latitude, longitude, latitudeWGS84, longitudeWGS84,
                date_opened, date_closed, site_link
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (site_code) DO UPDATE SET
                site_name = EXCLUDED.site_name,
                site_type = EXCLUDED.site_type,
                local_authority_name = EXCLUDED.local_authority_name,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                latitudeWGS84 = EXCLUDED.latitudeWGS84,
                longitudeWGS84 = EXCLUDED.longitudeWGS84,
                date_opened = EXCLUDED.date_opened,
                date_closed = EXCLUDED.date_closed,
                site_link = EXCLUDED.site_link;
        """, (
            site["site_code"],
            site["site_name"],
            site["site_type"],
            site["local_authority_name"],
            site["latitude"],
            site["longitude"],
            site["latitudeWGS84"],
            site["longitudeWGS84"],
            site["date_opened"],
            site["date_closed"],
            site["site_link"]
        ))
        conn.commit()
        print(f"✅ Inserted/Updated site {site['site_code']}")

        # Call cleanup after each insert/update
        remove_duplicates()

    except Exception as e:
        print(f"❌ Error inserting site {site['site_code']}: {e}")
        conn.rollback()
