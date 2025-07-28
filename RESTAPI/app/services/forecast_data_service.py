import joblib
import os
import redis
import pickle
import requests
import numpy as np
from datetime import datetime
from typing import List
from app.schemas.forecast_data import TrafficData, ForecastResponse
from app.models.site import Site
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sklearn.preprocessing import StandardScaler,LabelEncoder

MODEL_DIR = "./forecast_model"
OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY","0fb0f50c2badb10762006b6384c5b5da")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://pro.openweathermap.org/data/2.5/forecast/hourly"

INVERSE_TRAFFIC = {
    "low": "high",
    "moderate_low": "moderate_high",
    "moderate": "moderate",
    "moderate_high": "moderate_low",
    "high": "low"
}

def get_pollutant_targets_from_redis():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    targets_blob = r.get("forecast:numeric_targets")
    if targets_blob:
        return pickle.loads(targets_blob)
    return ["aqi", "co", "no", "no2", "o3", "so2", "pm2_5", "pm10", "nh3"]  # fallback

async def get_forecast_data(db: AsyncSession, target_dt: datetime, traffic_data: List[TrafficData]) -> List[ForecastResponse]:
    stmt = select(Site).distinct()
    result = await db.execute(stmt)
    sites = result.scalars().all()

    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))

    POLLUTANTS = get_pollutant_targets_from_redis()
    models = {}
    for pol in POLLUTANTS:
        path = os.path.join(MODEL_DIR, f"model_regression_{pol}.json")
        if os.path.exists(path):
            models[pol] = joblib.load(path)

    site_codes = [s.site_code for s in sites]
    site_encoder = LabelEncoder()
    site_encoder.fit(site_codes)

    forecast_results = []
    now = datetime.utcnow()
    is_now = (target_dt.date() == now.date() and target_dt.hour == now.hour)

    for td in traffic_data:
        matching_sites = [s for s in sites if round(s.latitude, 4) == round(td.latitude, 4) and round(s.longitude, 4) == round(td.longitude, 4)]
        if not matching_sites:
            continue
        site = matching_sites[0]

        # Fetch weather
        params = {"lat": td.latitude, "lon": td.longitude, "appid": OPENWEATHER_KEY, "units": "metric"}
        if is_now:
            resp = requests.get(WEATHER_URL, params=params)
            print(WEATHER_URL)
            print(params)
            data = resp.json()
        else:
            resp = requests.get(FORECAST_URL, params=params)
            print(FORECAST_URL)
            print(params)
            forecast = resp.json().get("list", [])
            data = next((f for f in forecast if f["dt_txt"].startswith(target_dt.strftime("%Y-%m-%d %H"))), None)
            if not data:
                continue

        weather = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {}).get("all", 0)

        traffic_density_val = list(INVERSE_TRAFFIC.keys()).index(td.traffic_density)
        traffic_flow_val = list(INVERSE_TRAFFIC.keys()).index(INVERSE_TRAFFIC.get(td.traffic_density, "moderate"))
        site_code_enc = int(site_encoder.transform([site.site_code])[0])

        features = [
            site_code_enc,
            site.latitude, site.longitude,
            target_dt.hour, target_dt.day, target_dt.month, target_dt.weekday(),
            traffic_flow_val, traffic_density_val,
            weather.get("temp", 0), weather.get("feels_like", 0), weather.get("pressure", 0),
            weather.get("humidity", 0), weather.get("temp", 0) - 5,
            clouds, wind.get("speed", 0), wind.get("deg", 0)
        ]

        if len(features) != scaler.n_features_in_:
            continue  # Skip if feature count mismatches model expectation

        X_scaled = scaler.transform(np.array([features]))
        predictions = {}
        for pol, model in models.items():
            predictions[pol] = round(float(model.predict(X_scaled)[0]), 2)

        dew_point = round(weather.get("temp", 0) - 5,2)

        forecast_results.append(ForecastResponse(
            site_code=site.site_code,
            site_name=site.site_name,
            site_type=site.site_type,
            latitude=site.latitude,
            longitude=site.longitude,
            datetime=target_dt,
            aqi=int(round(predictions.get("aqi", 0))),
            co=predictions.get("co", 0.0),
            no=predictions.get("no", 0.0),
            no2=predictions.get("no2", 0.0),
            o3=predictions.get("o3", 0.0),
            so2=predictions.get("so2", 0.0),
            pm2_5=predictions.get("pm2_5", 0.0),
            pm10=predictions.get("pm10", 0.0),
            nh3=predictions.get("nh3", 0.0),
            temp=weather.get("temp", 0),
            feels_like=weather.get("feels_like", 0),
            pressure=weather.get("pressure", 0),
            humidity=weather.get("humidity", 0),
            dew_point=dew_point,
            wind_speed=wind.get("speed", 0),
            wind_deg=wind.get("deg", 0),
            traffic_flow=INVERSE_TRAFFIC.get(td.traffic_density, "moderate"),
            traffic_density=td.traffic_density
        ))

    return forecast_results
