import pandas as pd
import numpy as np
import psycopg2
import joblib
import json
from kafka import KafkaProducer
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.utils import class_weight
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedShuffleSplit
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping
# import tensorflow_addons as tfa
# Optional: uncomment the next line if tensorflow_addons is installed
# import tensorflow_addons as tfa
from datetime import datetime, timedelta
import time
import requests
import os

MODEL_DIR = "./models"
REST_HOST = os.getenv("REST_HOST", "localhost")
REST_PORT = os.getenv("REST_PORT", "8000")

def inverse_density(flow):
    mapping = {
        "low": "high",
        "moderate_low": "moderate_high",
        "moderate": "moderate",
        "moderate_high": "moderate_low",
        "high": "low"
    }
    return mapping.get(flow, "moderate")

def upload_model_to_api(model_path):
    url = f"http://{REST_HOST}:{REST_PORT}/models/upload-model/"
    try:
        with open(model_path, "rb") as f:
            response = requests.post(url, files={"file": (os.path.basename(model_path), f)})
        if response.status_code == 200:
            print(response.json()["message"])
        else:
            print("❌ Upload failed:", response.content)
    except Exception as e:
        print(f"❌ Upload error for {model_path}: {e}")

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

    print("\u2705 Starting LSTM-based synthetic traffic data generation...")

    aqi_df = pd.read_sql("SELECT * FROM aqi_table;", conn)
    weather_df = pd.read_sql("SELECT * FROM weather_table;", conn)
    site_df = pd.read_sql("SELECT DISTINCT latitude, longitude FROM site_table WHERE latitude IS NOT NULL AND longitude IS NOT NULL;", conn)

    aqi_df["measurement_datetime"] = pd.to_datetime(aqi_df["measurement_datetime"]).dt.tz_localize(None)
    weather_df["timestamp"] = pd.to_datetime(weather_df["timestamp"]).dt.tz_localize(None)

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
        print("\u274c No merged data available.")
        return

    merged_df["measurement_timestamp"] = merged_df["measurement_datetime"].apply(lambda x: x.timestamp())
    merged_df["hour"] = merged_df["measurement_datetime"].dt.hour
    merged_df["weekday"] = merged_df["measurement_datetime"].dt.weekday

    aqi_features = ["pm2_5", "pm10", "no2", "so2", "co", "o3"]
    weather_features = ["temp", "pressure", "humidity", "wind_speed", "clouds", "visibility"]
    time_features = ["latitude", "longitude", "measurement_timestamp", "hour", "weekday"]
    features = aqi_features + weather_features + time_features

    merged_df["aqi_score"] = (
        merged_df["no2"] * 4 +
        merged_df["pm2_5"] * 3 +
        merged_df["pm10"] * 2 +
        (100 - merged_df["wind_speed"] * 10) +
        merged_df["clouds"]
    )

    quantiles = merged_df["aqi_score"].quantile([0.2, 0.4, 0.6, 0.8]).values

    def map_flow(aqi):
        if aqi < quantiles[0]: return "low"
        elif aqi < quantiles[1]: return "moderate_low"
        elif aqi < quantiles[2]: return "moderate"
        elif aqi < quantiles[3]: return "moderate_high"
        else: return "high"

    merged_df["traffic_flow"] = merged_df["aqi_score"].apply(map_flow)
    merged_df["traffic_density"] = merged_df["traffic_flow"].apply(inverse_density)

    flow_order = ["low", "moderate_low", "moderate", "moderate_high", "high"]
    flow_encoder = LabelEncoder()
    flow_encoder.fit(flow_order)
    merged_df["flow_label"] = flow_encoder.transform(merged_df["traffic_flow"])
    merged_df = merged_df.sort_values("measurement_datetime")

    sequence_length = 24
    X_sequences, y_labels = [], []
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

    # Stratified split
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
    for train_idx, test_idx in sss.split(X_scaled, y_labels):
        X_train, X_test = X_scaled[train_idx], X_scaled[test_idx]
        y_train, y_test = y_labels[train_idx], y_labels[test_idx]

    class_weights = class_weight.compute_class_weight(class_weight='balanced', classes=np.unique(y_train), y=y_train)
    class_weight_dict = dict(enumerate(class_weights))

    model = keras.Sequential([
        layers.Input(shape=(sequence_length, X_scaled.shape[-1])),
        layers.LSTM(16, return_sequences=True),
        layers.LSTM(16),
        layers.Dense(32, activation="relu"),
        layers.Dropout(0.1),
        layers.Dense(5, activation="softmax")
    ])

    model.compile(optimizer="adam", loss='sparse_categorical_crossentropy', metrics=["accuracy"])
    early_stopping = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, epochs=100, batch_size=50, validation_split=0.1, callbacks=[early_stopping], class_weight=class_weight_dict)

    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"\u2705 LSTM Model - Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")

    y_pred = np.argmax(model.predict(X_test), axis=1)
    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred, target_names=flow_order))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synthetic_lstm_stats (
            id SERIAL PRIMARY KEY,
            model_name TEXT,
            test_loss DOUBLE PRECISION,
            test_accuracy DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cursor.execute("""
        INSERT INTO synthetic_lstm_stats (model_name, test_loss, test_accuracy)
        VALUES (%s, %s, %s);
    """, ("lstm_traffic_model", float(loss), float(accuracy)))
    conn.commit()

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(scaler, f"{MODEL_DIR}/lstm_scaler.joblib")
    upload_model_to_api(f"{MODEL_DIR}/lstm_scaler.joblib")
    joblib.dump(flow_encoder, f"{MODEL_DIR}/flow_encoder.joblib")
    upload_model_to_api(f"{MODEL_DIR}/flow_encoder.joblib")
    model_path = f"{MODEL_DIR}/lstm_traffic_model.keras"
    model.save(model_path)
    upload_model_to_api(model_path)

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
    print("\u2705 Traffic data production completed.")

if __name__ == "__main__":
    produce_traffic_data()
