from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.schemas.forecast_data import ForecastRequest, ForecastResponse
from app.services import forecast_data_service
from datetime import datetime
from typing import List

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=List[ForecastResponse])
async def get_forecast_data(req: ForecastRequest, db: AsyncSession = Depends(get_db)):
    print(req)
    if req.datetime.replace(minute=0,second=0, microsecond=0) < datetime.now().replace(minute=0,second=0, microsecond=0):
        raise HTTPException(status_code=400, detail="Datetime must be in the future or present.")

    results = await forecast_data_service.get_forecast_data(db, req.datetime, req.traffic_data)

    if not results:
        raise HTTPException(status_code=404, detail="No forecast data available for the specified datetime. Possibly forecast API not reached")

    return results