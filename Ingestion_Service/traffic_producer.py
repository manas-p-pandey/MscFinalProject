import pandas as pd
import numpy as np
import psycopg2
import joblib
import json
from kafka import KafkaProducer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from tensorflow import keras
from tensorflow.keras import layers
from datetime import datetime, timedelta
import time

def produce_traffic_data():
    KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
    POSTGRES_HOST = "db"
    POSTGRES_DB = "mscds"
    POSTGRES_USER = "postgres"
    POSTGRES_PASSWORD = "Admin123"

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    cursor = conn.cursor()

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    print("✅ Starting LSTM-based synthetic traffic data generation...")

    # Load data
    aqi_df = pd.read_sql("SELECT * FROM aqi_table;", conn)
    weather_df = pd.read_sql("SELECT * FROM weather_table;", conn)
    site_df = pd.read_sql("SELECT DISTINCT latitude, longitude FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;", conn)

    aqi_df["measurement_datetime"] = pd.to_datetime(aqi_df["measurement_datetime"]).dt.tz_localize(None)
    weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"]).dt.tz_localize(None)

    # Merge
    merged_df = pd.merge_asof(
        aqi_df.sort_values("measurement_datetime"),
        weather_df.sort_values("timestamp"),
        left_on="measurement_datetime",
        right_on="timestamp",
        by=["latitude", "longitude"],
        direction="nearest",
        tolerance=pd.Timedelta("30m")
    )

    merged_df = merged_df.dropna()

    if merged_df.empty:
        print("❌ No merged data available.")
        return

    # Features
    aqi_features = ["pm2_5", "pm10", "no2", "so2", "co", "o3"]
    weather_features = ["temp", "pressure", "humidity", "wind_speed", "clouds", "visibility"]
    location_features = ["latitude", "longitude", "measurement_timestamp"]
    features = aqi_features + weather_features + location_features

    merged_df["measurement_timestamp"] = merged_df["measurement_datetime"].apply(lambda x: x.timestamp())

    merged_df["score"] = (
        merged_df["no2"] * 4 +
        merged_df["pm2_5"] * 3 +
        merged_df["pm10"] * 2 +
        (100 - merged_df["wind_speed"] * 10) +
        merged_df["clouds"]
    )

    threshold_high = merged_df["score"].quantile(0.66)
    threshold_mod = merged_df["score"].quantile(0.33)

    def assign_flow_category(score):
        if score >= threshold_high:
            return "high"
        elif score >= threshold_mod:
            return "moderate"
        else:
            return "low"

    merged_df["traffic_flow"] = merged_df["score"].apply(assign_flow_category)

    def inverse_density(flow):
        if flow == "high":
            return "low"
        elif flow == "moderate":
            return "moderate"
        else:
            return "high"

    merged_df["traffic_density"] = merged_df["traffic_flow"].apply(inverse_density)

    flow_encoder = LabelEncoder()
    merged_df["flow_label"] = flow_encoder.fit_transform(merged_df["traffic_flow"])

    merged_df = merged_df.sort_values("measurement_datetime")

    sequence_length = 24
    X_sequences = []
    y_labels = []

    for i in range(sequence_length, len(merged_df)):
        sequence = merged_df[features].iloc[i-sequence_length:i].values
        X_sequences.append(sequence)
        y_labels.append(merged_df["flow_label"].iloc[i])

    X_sequences = np.array(X_sequences)
    y_labels = np.array(y_labels)

    scaler = StandardScaler()
    flat_X = X_sequences.reshape(-1, X_sequences.shape[-1])
    scaled_flat_X = scaler.fit_transform(flat_X)
    X_scaled = scaled_flat_X.reshape(X_sequences.shape)

    split_idx = int(0.8 * len(X_scaled))
    X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
    y_train, y_test = y_labels[:split_idx], y_labels[split_idx:]

    model = keras.Sequential([
        layers.LSTM(64, input_shape=(sequence_length, X_scaled.shape[-1])),
        layers.Dense(32, activation="relu"),
        layers.Dense(3, activation="softmax")
    ])

    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(X_train, y_train, epochs=5, batch_size=32, validation_split=0.1)

    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"✅ LSTM Model - Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")

    joblib.dump(scaler, "scaler.save")
    joblib.dump(flow_encoder, "flow_encoder.save")
    model.save("traffic_lstm_model.keras")

    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()

    for index, site in site_df.iterrows():
        lat = float(site["latitude"])
        lon = float(site["longitude"])

        cursor.execute("""
            SELECT DISTINCT measurement_datetime FROM traffic_table
            WHERE latitude = %s AND longitude = %s;
        """, (lat, lon))
        existing = set(row[0].replace(minute=0, second=0, microsecond=0) for row in cursor.fetchall())

        expected_hours = []
        current = start_date.replace(minute=0, second=0, microsecond=0)
        while current <= end_date:
            expected_hours.append(current)
            current += timedelta(hours=1)

        missing_hours = [dt for dt in expected_hours if dt not in existing]
        print(f"🔍 Traffic: {lat}, {lon} - Missing: {len(missing_hours)} hours")

        for dt in missing_hours:
            # Extra explicit check before generating payload
            cursor.execute("""
                SELECT 1 FROM traffic_table
                WHERE latitude = %s AND longitude = %s AND measurement_datetime = %s
            """, (lat, lon, dt))
            if cursor.fetchone():
                print(f"⏭️ Skipping existing traffic record at {dt}")
                continue

            last_seq = merged_df[features].iloc[-sequence_length:].values.copy()
            last_seq[-1][-3] = lat
            last_seq[-1][-2] = lon
            last_seq[-1][-1] = dt.timestamp()

            last_seq_scaled = scaler.transform(last_seq).reshape(1, sequence_length, -1)

            pred_probs = model.predict(last_seq_scaled)[0]
            pred_label = np.argmax(pred_probs)
            flow_category = flow_encoder.inverse_transform([pred_label])[0]
            density_category = inverse_density(flow_category)

            payload = {
                "measurement_datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "latitude": lat,
                "longitude": lon,
                "traffic_flow": flow_category,
                "traffic_density": density_category
            }

            producer.send("traffic_data", payload)
            print(f"✅ Sent: {payload}")

        producer.flush()
    print("✅ Traffic data production completed.")

if __name__ == "__main__":
    produce_traffic_data()
