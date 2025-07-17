# [Place the full final forecast_producer.py code here]import pandas as pd
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
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor, XGBClassifier
from kafka import KafkaProducer

# CONFIG
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mscds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Admin123")

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

traffic_map_rev = {0: "low", 1: "moderate", 2: "high"}

def load_data():
    query = """
    SELECT site_code, site_name, site_type, latitude, longitude, datetime, day_of_week, 
    aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3, temp, feels_like, pressure, humidity, 
    dew_point, clouds, wind_speed, wind_deg, weather_main, weather_description, 
    traffic_flow, traffic_density
    FROM public.ml_data_view
    ORDER BY datetime, site_code;
    """
    df = pd.read_sql(query, con=engine)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

def preprocess_data(df):
    df['traffic_flow'] = df['traffic_flow'].str.strip().str.lower().map({'low': 0, 'moderate': 1, 'high': 2})
    df['traffic_density'] = df['traffic_density'].str.strip().str.lower().map({'low': 0, 'moderate': 1, 'high': 2})

    le_site = LabelEncoder()
    df['site_code_enc'] = le_site.fit_transform(df['site_code'])

    df['hour'] = df['datetime'].dt.hour
    df['day'] = df['datetime'].dt.day
    df['month'] = df['datetime'].dt.month
    df['weekday'] = df['datetime'].dt.weekday

    feature_cols = ['site_code_enc', 'latitude', 'longitude', 'hour', 'day', 'month', 'weekday']
    X = df[feature_cols]

    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    if os.path.exists(scaler_path):
        scaler = joblib.load(scaler_path)
    else:
        scaler = StandardScaler()
        scaler.fit(X)
        joblib.dump(scaler, scaler_path)

    X_scaled = scaler.transform(X)
    return X_scaled, df, scaler, le_site

def retrain_models(X_scaled, df):
    numeric_cols = ['aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3',
                    'temp', 'feels_like', 'pressure', 'humidity', 'dew_point',
                    'clouds', 'wind_speed', 'wind_deg']
    classification_cols = ['traffic_flow', 'traffic_density']

    for target in numeric_cols:
        y = df[target]
        model_path = os.path.join(MODEL_DIR, f"model_regression_{target}.json")
        model = XGBRegressor()
        if os.path.exists(model_path):
            model.load_model(model_path)
        model.fit(X_scaled, y)
        model.save_model(model_path)

    for target in classification_cols:
        y = df[target]
        model_path = os.path.join(MODEL_DIR, f"model_classification_{target}.json")
        model = XGBClassifier()
        if os.path.exists(model_path):
            model.load_model(model_path)
        model.fit(X_scaled, y)
        model.save_model(model_path)

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
                'weekday': future_dt.weekday()
            }
            combined.append(row_dict)

    forecast_df = pd.DataFrame(combined)
    forecast_df['site_code_enc'] = le_site.transform(forecast_df['site_code'])

    feature_cols = ['site_code_enc', 'latitude', 'longitude', 'hour', 'day', 'month', 'weekday']
    X_forecast = forecast_df[feature_cols]
    X_scaled = scaler.transform(X_forecast)

    for target in [
        'aqi', 'co', 'no', 'no2', 'o3', 'so2', 'pm2_5', 'pm10', 'nh3',
        'temp', 'feels_like', 'pressure', 'humidity', 'dew_point',
        'clouds', 'wind_speed', 'wind_deg'
    ]:
        model = XGBRegressor()
        model.load_model(os.path.join(MODEL_DIR, f"model_regression_{target}.json"))
        forecast_df[target] = model.predict(X_scaled)

    for target in ['traffic_flow', 'traffic_density']:
        model = XGBClassifier()
        model.load_model(os.path.join(MODEL_DIR, f"model_classification_{target}.json"))
        preds = model.predict(X_scaled)
        forecast_df[target] = [traffic_map_rev.get(int(p), "unknown") for p in preds]

    return forecast_df

def send_to_kafka(forecast_df):
    for _, row in forecast_df.iterrows():
        message = row.to_dict()
        if isinstance(message["datetime"], (pd.Timestamp, datetime)):
            message["datetime"] = message["datetime"].isoformat()
        producer.send(KAFKA_TOPIC, message)
    producer.flush()

if __name__ == "__main__":
    print("✅ Forecast producer started.")
    print(f"⏰ Waiting to start next batch at {datetime.today().replace(hour=0, minute=30, second=0, microsecond=0)+timedelta(days=1)}")
    while True:
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second

        # Check if it's the start of a new hour and hasn't been run in this hour
        if current_minute == 30 and current_second>=0 and current_second < 10 and current_hour ==0:
            print(f"[{now}] Running producer workflow...")
            try:
                df = load_data()
                X_scaled, df_processed, scaler, le_site = preprocess_data(df)
                retrain_models(X_scaled, df_processed)
                forecast_df = generate_forecast_rows(df, scaler, le_site)
                send_to_kafka(forecast_df)
                print(f"[{datetime.now()}] ✅ Forecast data sent to Kafka. Sleeping until next run...")
                
            except Exception as e:
                print(f"❌ Error during producer run: {e}")
            print(f"⏰ Waiting to start next batch at {now.replace(hour=0, minute=30, second=0, microsecond=0)+timedelta(days=1)}")
        else:
            time.sleep(1)