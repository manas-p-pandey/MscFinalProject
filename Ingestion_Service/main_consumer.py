import threading
import aqi_consumer
import site_consumer
import traffic_consumer
import weather_consumer

if __name__ == "__main__":
    print("🚀 Starting all consumers...")

    threads = []

    threads.append(threading.Thread(target=site_consumer.run))
    threads.append(threading.Thread(target=aqi_consumer.run))
    threads.append(threading.Thread(target=weather_consumer.run))
    threads.append(threading.Thread(target=traffic_consumer.run))

    for t in threads:
        t.start()

    for t in threads:
        t.join()
