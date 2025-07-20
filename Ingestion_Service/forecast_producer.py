import numpy as np
import joblib
import time
from datetime import datetime
import os
import json
import psycopg2
import pandas as pd
import requests

from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import redis
import pickle
from xgboost import XGBRegressor

# CONFIG
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REST_HOST = os.getenv("REST_HOST","localhost")
REST_PORT = os.getenv("REST_PORT","8000")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

MODEL_DIR = "./forecast_model"
POSTGRES_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"
engine = create_engine(POSTGRES_URI)

conn = psycopg2.connect(
    host=POSTGRES_HOST,
    database=POSTGRES_DB,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD
)

def load_data():
    query = """
    SELECT site_code, latitude, longitude, datetime, traffic_flow, traffic_density,
           temp, feels_like, pressure, humidity, dew_point, clouds, wind_speed, wind_deg,
           aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
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

    feature_cols = [
        'site_code_enc', 'latitude', 'longitude', 'hour', 'day', 'month', 'weekday',
        'traffic_flow', 'traffic_density',
        'temp', 'feels_like', 'pressure', 'humidity', 'dew_point', 'clouds', 'wind_speed', 'wind_deg'
    ]
    X = df[feature_cols]

    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
    else:
        scaler = StandardScaler()
        scaler.fit(X)
        joblib.dump(scaler, scaler_path)

    X_scaled = scaler.transform(X)

    regression_targets = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3']
    y = df[regression_targets]
    redis_client.set("forecast:feature_columns", pickle.dumps(feature_cols))
    redis_client.set("forecast:target_columns", pickle.dumps(regression_targets))

    return X_scaled, y, df, scaler, le_site

def retrain_models(X_scaled, y):
    os.makedirs(MODEL_DIR, exist_ok=True)
    cursor = conn.cursor()

    for col in y.columns:
        model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
        model.fit(X_scaled, y[col])

        y_pred = model.predict(X_scaled)

        rmse = mean_squared_error(y[col], y_pred, squared=False)
        mae = mean_absolute_error(y[col], y_pred)
        r2 = r2_score(y[col], y_pred)

        print(f"\n📊 Metrics for {col} — RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")

        # Save the model
        model_path = os.path.join(MODEL_DIR, f"model_regression_{col}.json")
        joblib.dump(model, model_path)
        print(f"✅ Retrained and saved model: {model_path}")

        # Insert stats into regressor_stats table
        insert_query = """
            INSERT INTO public.regressor_stats (model, rmse, mae, r2, created_at)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (col, rmse, mae, r2, datetime.now()))

        # Upload model to API
        upload_model_to_api(model_path)

    conn.commit()
    cursor.close()

def upload_model_to_api(model_path):
    url = f"http://{REST_HOST}:{REST_PORT}/models/upload-model/"  # container or hostname for FastAPI
    try:
        with open(model_path, "rb") as f:
            response = requests.post(url, files={"file": (os.path.basename(model_path), f)})
        if response.status_code == 200:
            print(response.json()["message"])
        else:
            print("❌ Upload failed:", response.content)
    except Exception as e:
        print(f"❌ Upload error for {model_path}: {e}")

def produce_forecast_data():
    print("\u2705 Forecast retrainer started.")
    try:
        print("Loading data from postgres...")
        df = load_data()
        print("Preprocessing and scaling...")
        X_scaled, y, df_processed, scaler, le_site = preprocess_data(df)
        print("Retraining models...")
        retrain_models(X_scaled, y)
        print(f"[{datetime.now()}] \u2705 Model retraining complete.")

    except Exception as e:
        print(f"\u274c Error: {e}")

if __name__ == "__main__":
    produce_forecast_data()
