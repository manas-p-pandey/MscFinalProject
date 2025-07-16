import pandas as pd
import numpy as np
import joblib
import time
import datetime
import os
import json
import psycopg2

from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor, XGBClassifier
from kafka import KafkaProducer

# ==========================
# CONFIG
# ==========================
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

# ==========================
# Helper: Load Data
# ==========================
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

# ==========================
# Helper: Preprocess Data
# ==========================
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

# ==========================
# Helper: Retrain Models
# ==========================
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

        y_pred = model.predict(X_scaled)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        mae = mean_absolute_error(y, y_pred)
        r2 = r2_score(y, y_pred)

        stats_df = pd.DataFrame({
            'model': [target],
            'rmse': [rmse],
            'mae': [mae],
            'r2': [r2],
            'created_at': [datetime.datetime.now()]
        })
        stats_df.to_sql("regressor_stats", con=engine, if_exists='append', index=False)

    for target in classification_cols:
        y = df[target]
        model_path = os.path.join(MODEL_DIR, f"model_classification_{target}.json")
        model = XGBClassifier()
        if os.path.exists(model_path):
            model.load_model(model_path)
        model.fit(X_scaled, y)
        model.save_model(model_path)

        acc = model.score(X_scaled, y)
        stats_df = pd.DataFrame({
            'model': [target],
            'accuracy': [acc],
            'created_at': [datetime.datetime.now()]
        })
        stats_df.to_sql("categorical_stats", con=engine, if_exists='append', index=False)

# ==========================
# Helper: Generate Forecast Rows
# ==========================
def generate_forecast_rows(df, scaler, le_site):
    predictor_cols = ['site_code', 'latitude', 'longitude']
    distinct_predictors = df[predictor_cols].drop_duplicates()

    future_dates = pd.date_range(datetime.datetime.now().replace(minute=0, second=0, microsecond=0),
                                 periods=7*24+1, freq='H')

    combined = []
    for _, row in distinct_predictors.iterrows():
        for future_dt in future_dates:
            row_dict = {}
            row_dict['site_code'] = row['site_code']
            row_dict['latitude'] = row['latitude']
            row_dict['longitude'] = row['longitude']
            row_dict['datetime'] = future_dt
            row_dict['hour'] = future_dt.hour
            row_dict['day'] = future_dt.day
            row_dict['month'] = future_dt.month
            row_dict['weekday'] = future_dt.weekday()
            combined.append(row_dict)

    forecast_df = pd.DataFrame(combined)

    forecast_df['site_code_enc'] = le_site.transform(forecast_df['site_code'])

    feature_cols = ['site_code_enc', 'latitude', 'longitude', 'hour', 'day', 'month', 'weekday']
    X_forecast = forecast_df[feature_cols]
    X_scaled = scaler.transform(X_forecast)
    forecast_df[feature_cols] = X_scaled

    return forecast_df

# ==========================
# Helper: Send to Kafka
# ==========================
def send_to_kafka(forecast_df):
    for _, row in forecast_df.iterrows():
        message = row.to_dict()

        if isinstance(message['datetime'], (pd.Timestamp, datetime.datetime)):
            message['datetime'] = message['datetime'].isoformat()

        producer.send(KAFKA_TOPIC, message)
    producer.flush()

# ==========================
# Main loop
# ==========================
if __name__ == "__main__":
    print("✅ Forecast producer started.")

    try:
        df = load_data()
        X_scaled, df_processed, scaler, le_site = preprocess_data(df)
        retrain_models(X_scaled, df_processed)

        forecast_df = generate_forecast_rows(df, scaler, le_site)
        send_to_kafka(forecast_df)

        print(f"[{datetime.datetime.now()}] ✅ Forecast data sent to Kafka. Sleeping until next run...")
                
    except Exception as e:
        print(f"❌ Error during producer run: {e}")

    while True:
        current_time = datetime.datetime.now()
        if current_time.minute == 30:
            print(f"[{current_time}] Running producer workflow...")

            try:
                df = load_data()
                X_scaled, df_processed, scaler, le_site = preprocess_data(df)
                retrain_models(X_scaled, df_processed)

                forecast_df = generate_forecast_rows(df, scaler, le_site)
                send_to_kafka(forecast_df)

                print(f"[{datetime.datetime.now()}] ✅ Forecast data sent to Kafka. Sleeping until next run...")
                
            except Exception as e:
                print(f"❌ Error during producer run: {e}")

        else:
            time.sleep(1)
