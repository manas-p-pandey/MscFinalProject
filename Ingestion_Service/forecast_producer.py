import numpy as np
import joblib
import time
from datetime import datetime, timedelta
import os
import json
import psycopg2
import pandas as pd

from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler, LabelEncoder
from kafka import KafkaProducer
import redis
import pickle

# CONFIG
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

MODEL_DIR = "./forecast_model"
KAFKA_TOPIC = "forecast_data"

POSTGRES_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
engine = create_engine(POSTGRES_URI)

conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def load_data():
    query = """
    SELECT site_code, latitude, longitude, datetime, traffic_flow, traffic_density
    FROM public.historical_data_view
    ORDER BY datetime, site_code;
    """
    df = pd.read_sql(query, con=engine)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

def preprocess_data(df):
    flow_mapping = {"low": 0, "moderate_low": 1, "moderate": 2, "moderate_high": 3, "high": 4}
    df['traffic_flow'] = df['traffic_flow'].str.strip().str.lower().map(flow_mapping)
    df['traffic_density'] = df['traffic_density'].str.strip().str.lower().map(flow_mapping)

    le_site = LabelEncoder()
    df['site_code_enc'] = le_site.fit_transform(df['site_code'])

    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.day
    df['month'] = df['datetime'].dt.month
    df['weekday'] = df['datetime'].dt.weekday

    feature_cols = ['site_code_enc', 'latitude', 'longitude', 'hour', 'day', 'month', 'weekday', 'traffic_flow', 'traffic_density']
    X = df[feature_cols]

    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
    else:
        scaler = StandardScaler()
        scaler.fit(X)
        joblib.dump(scaler, scaler_path)

    X_scaled = scaler.transform(X)

    y = df['aqi']
    redis_client.set("forecast:feature_columns", pickle.dumps(feature_cols))

    return X_scaled, df, scaler, le_site

def load_model():
    model_path = os.path.join(MODEL_DIR, "model_regression_aqi.pkl")
    model = joblib.load(model_path)
    return model

def generate_forecast_rows(df, scaler, le_site):
    predictor_cols = ['site_code', 'latitude', 'longitude']
    distinct_predictors = df[predictor_cols].drop_duplicates()

    future_dates = pd.date_range(datetime.now().replace(minute=0, second=0, microsecond=0),
                                 periods=7*24+1, freq='H')

    combined = []
    for _, row in distinct_predictors.iterrows():
        for future_dt in future_dates:
            row_dict = {
                'site_code': row['site_code'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'datetime': future_dt,
                'hour': future_dt.hour,
                'day': future_dt.day,
                'month': future_dt.month,
                'weekday': future_dt.weekday,
                'traffic_flow': 2,  # default moderate
                'traffic_density': 2  # default moderate
            }
            combined.append(row_dict)

    forecast_df = pd.DataFrame(combined)
    forecast_df['site_code_enc'] = le_site.transform(forecast_df['site_code'])

    feature_cols = pickle.loads(redis_client.get("forecast:feature_columns"))
    X_forecast = forecast_df[feature_cols]
    X_scaled = scaler.transform(X_forecast)

    model = load_model()
    forecast_df['aqi'] = model.predict(X_scaled)

    return forecast_df

def send_to_kafka(forecast_df):
    for _, row in forecast_df.iterrows():
        message = row.to_dict()
        if isinstance(message["datetime"], (pd.Timestamp, datetime)):
            message["datetime"] = message["datetime"].isoformat()
        producer.send(KAFKA_TOPIC, message)
    producer.flush()

def produce_forecast_data():
    print("\u2705 Forecast producer started.")
    try:
        print("Loading data from postgres...")
        df = load_data()
        print("Preprocessing and scaling...")
        X_scaled, df_processed, scaler, le_site = preprocess_data(df)
        print("Generating forecast data...")
        forecast_df = generate_forecast_rows(df, scaler, le_site)
        print("Sending forecast to Kafka...")
        send_to_kafka(forecast_df)
        print(f"[{datetime.now()}] \u2705 Forecast data sent.")

    except Exception as e:
        print(f"\u274c Error: {e}")

if __name__ == "__main__":
    produce_forecast_data()
