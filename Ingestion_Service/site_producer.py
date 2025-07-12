import requests
from kafka import KafkaProducer
import json
import time
import os

def produce_site_data():
    # Config
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

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

    # Send to Kafka
    for site in westminster_sites:
        payload = {
            "site_code": site["@SiteCode"],
            "site_name": site["@SiteName"],
            "site_type": site["@SiteType"],
            "local_authority_name": site["@LocalAuthorityName"],
            "latitude": float(site["@Latitude"]) if site.get("@Latitude") not in (None, "", " ") else None,
            "longitude": float(site["@Longitude"]) if site.get("@Longitude") not in (None, "", " ") else None,
            "latitudeWGS84": float(site["@LatitudeWGS84"]) if site.get("@LatitudeWGS84") not in (None, "", " ") else None,
            "longitudeWGS84": float(site["@LongitudeWGS84"]) if site.get("@LongitudeWGS84") not in (None, "", " ") else None,
            "date_opened": site.get("@DateOpened") if site.get("@DateOpened") not in (None, "", " ") else None,
            "date_closed": site.get("@DateClosed") if site.get("@DateClosed") not in (None, "", " ") else None,
            "site_link": site.get("@SiteLink", "")
        }
        producer.send("site_data", payload)
        print(f"✅ Sent site metadata for {site['@SiteCode']}")

    producer.flush()
    print("✅ All Westminster site metadata produced.")

# Optional: if you want this script to run standalone as well
if __name__ == "__main__":
    produce_site_data()
    time.sleep(3600)
