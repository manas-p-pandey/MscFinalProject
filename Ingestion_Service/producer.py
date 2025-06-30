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

# Create tables if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS aqi_site_table (
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS aqi_table (
    id SERIAL PRIMARY KEY,
    site_code TEXT REFERENCES aqi_site_table(site_code),
    measurement_datetime TIMESTAMP NOT NULL,
    nitric_oxide DOUBLE PRECISION,
    nitrogen_dioxide DOUBLE PRECISION,
    oxides_of_nitrogen DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    pm25 DOUBLE PRECISION,
    UNIQUE (site_code, measurement_datetime)
);
""")
conn.commit()
print("✅ Tables checked or created.")

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Fetch site metadata
site_info_url = "https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSites/GroupName=London/Json"
response = requests.get(site_info_url)
data = response.json()

westminster_sites = [
    site for site in data["Sites"]["Site"]
    if site["@LocalAuthorityName"] == "Westminster"
]

# Insert or update site table
for site in westminster_sites:
    cursor.execute("""
        INSERT INTO aqi_site_table (site_code, site_name, site_type, local_authority_name, latitude, longitude, latitudeWGS84, longitudeWGS84, site_link)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (site_code) DO UPDATE SET
            site_name = EXCLUDED.site_name,
            site_type = EXCLUDED.site_type,
            local_authority_name = EXCLUDED.local_authority_name,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            latitudeWGS84 = EXCLUDED.latitudeWGS84,
            longitudeWGS84 = EXCLUDED.longitudeWGS84,
            site_link = EXCLUDED.site_link;
    """, (
        site["@SiteCode"],
        site["@SiteName"],
        site["@SiteType"],
        site["@LocalAuthorityName"],
        float(site["@Latitude"]),
        float(site["@Longitude"]),
        float(site["@LatitudeWGS84"]) if site.get("@LatitudeWGS84") not in (None, "", " ") else None,
        float(site["@LongitudeWGS84"]) if site.get("@LongitudeWGS84") not in (None, "", " ") else None,
        site.get("@SiteLink", "")
    ))
conn.commit()
print("✅ Westminster site metadata updated.")

# Extract site codes
site_codes = [site["@SiteCode"] for site in westminster_sites]
print("✅ Westminster site codes:", site_codes)

# Main loop
while True:
    for site_code in site_codes:
        cursor.execute("SELECT MAX(measurement_datetime) FROM aqi_table WHERE site_code = %s", (site_code,))
        result = cursor.fetchone()
        last_dt = result[0]

        if last_dt:
            start_date = last_dt.strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")

        end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"https://api.erg.ic.ac.uk/AirQuality/Data/Wide/Site/SiteCode={site_code}/StartDate={start_date}/EndDate={end_date}/Json"

        print(f"🔄 Fetching: {url}")

        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                data_json = resp.json()
                records = data_json.get("AirQualityData",{}).get("RawAQData", {}).get("Data", [])
                #data_columns = data_json.get("AirQualityData",{}).get("Columns",{}).get("Column",[])

                # Filter non-empty records
                filtered_records = [
                    rec for rec in records
                    if any(rec.get(f"@Data{i}") not in (None, "", " ") for i in range(1, 6))
                ]

                if filtered_records:
                    payload = {
                        "site_code": site_code,
                        #"data_columns": data_columns,
                        "data": filtered_records
                    }
                    producer.send("aqi_data", payload)
                    print(f"✅ Sent {len(filtered_records)} records to Kafka for {site_code}")
                else:
                    print(f"⚠️ No valid data to send for {site_code}")

            else:
                print(f"❌ Error fetching data: HTTP {resp.status_code}")

        except Exception as e:
            print(f"❌ Exception fetching data for {site_code}: {e}")

    producer.flush()
    time.sleep(3600)
