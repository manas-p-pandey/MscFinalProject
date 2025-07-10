import pandas as pd
import numpy as np
import psycopg2
import joblib
import json
from kafka import KafkaProducer
from sklearn.preprocessing import StandardScaler
from tensorflow import keras
from datetime import datetime
import time

# Config
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
POSTGRES_HOST = "db"
POSTGRES_DB = "mscds"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "Admin123"

# Connect to database
conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Loop forever every hour
while True:
    print("⏰ Running traffic data producer loop...")

    aqi_query = "SELECT * FROM aqi_table;"
    weather_query = "SELECT * FROM weather_table;"

    aqi_df = pd.read_sql(aqi_query, conn)
    weather_df = pd.read_sql(weather_query, conn)

    # Check columns
    print("AQI columns:", aqi_df.columns.tolist())

    # Convert timestamps and remove timezone
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
        tolerance=pd.Timedelta("1h")
    )

    merged_df = merged_df.dropna()

    aqi_features = ["pm2_5", "pm10", "no2", "so2", "co", "o3"]
    weather_features = ["temp", "pressure", "humidity", "wind_speed", "clouds", "visibility"]
    features = aqi_features + weather_features

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

    # Train model
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder

    flow_encoder = LabelEncoder()
    merged_df["flow_label"] = flow_encoder.fit_transform(merged_df["traffic_flow"])

    X = merged_df[features].fillna(0).values
    y = merged_df["flow_label"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    from tensorflow.keras import layers

    model = keras.Sequential([
        layers.Dense(64, activation="relu", input_shape=(len(features),)),
        layers.Dense(32, activation="relu"),
        layers.Dense(3, activation="softmax")
    ])

    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.1)

    joblib.dump(scaler, "scaler.save")
    joblib.dump(flow_encoder, "flow_encoder.save")
    model.save("traffic_flow_model.h5")

    # Producer loop
    for idx, row in merged_df.iterrows():
        input_data = row[features].values.reshape(1, -1)
        input_scaled = scaler.transform(input_data)

        pred_probs = model.predict(input_scaled)[0]
        pred_label = np.argmax(pred_probs)
        flow_category = flow_encoder.inverse_transform([pred_label])[0]

        if flow_category == "high":
            density_category = "low"
        elif flow_category == "moderate":
            density_category = "moderate"
        else:
            density_category = "high"

        payload = {
            "measurement_datetime": row["measurement_datetime"].strftime("%Y-%m-%d %H:%M:%S"),
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "traffic_flow": flow_category,
            "traffic_density": density_category
        }

        producer.send("traffic_data", payload)
        print(f"✅ Sent: {payload}")

    producer.flush()
    print("✅ Finished producing this batch of synthetic traffic data.")

    # Wait for one hour before next run
    print("⏰ Sleeping for 1 hour...")
    time.sleep(3600)
