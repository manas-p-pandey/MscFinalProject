import requests
import pandas as pd
from geopy.distance import geodesic
import psycopg2
from kafka import KafkaProducer
import json
import os
import time
from datetime import datetime, timedelta

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

# Kafka producer
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def get_congestion_data(start_date, end_date):
    endpoint = f"https://api.tfl.gov.uk/Road/all/Street/Disruption?startDate={start_date}&endDate={end_date}"
    response = requests.get(endpoint)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to fetch data: {response.status_code}")
        return []

def find_nearest_road(congestion_data, lat, lon):
    if not congestion_data:
        return None

    df = pd.DataFrame(congestion_data)
    if df.empty or 'startLat' not in df.columns or 'startLon' not in df.columns:
        return None

    df = df[df['startLat'].notnull() & df['startLon'].notnull()]

    if df.empty:
        return None

    df['distance'] = df.apply(
        lambda row: geodesic(
            (lat, lon),
            (row['startLat'], row['startLon'])
        ).km,
        axis=1
    )
    nearest_road = df.loc[df['distance'].idxmin()]
    return nearest_road

while True:
    try:
        # Fetch all unique lat/lon from site table
        cursor.execute("SELECT DISTINCT latitude, longitude, site_code FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;")
        locations = cursor.fetchall()

        # Calculate start and end date
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")

        congestion_data = get_congestion_data(start_date, end_date)

        for lat, lon, site_code in locations:
            nearest_road = find_nearest_road(congestion_data, lat, lon)
            if nearest_road is not None:
                payload = {
                    "site_code": site_code,
                    "latitude": lat,
                    "longitude": lon,
                    "road_name": nearest_road.get('streetName'),
                    "closure": nearest_road.get('closure'),
                    "directions": nearest_road.get('directions'),
                    "severity": nearest_road.get('severity'),
                    "category": nearest_road.get('category'),
                    "sub_category": nearest_road.get('subCategory'),
                    "comments": nearest_road.get('comments'),
                    "start_datetime": nearest_road.get('startDateTime'),
                    "end_datetime": nearest_road.get('endDateTime'),
                    "distance_km": nearest_road['distance']
                }
                producer.send("traffic_data", payload)
                print(f"✅ Sent traffic data for {site_code}: {payload['road_name']} ({payload['severity']})")

        producer.flush()

    except Exception as e:
        print(f"❌ Exception during traffic data ingestion: {e}")

    time.sleep(3600)  # Wait 1 hour before next round
