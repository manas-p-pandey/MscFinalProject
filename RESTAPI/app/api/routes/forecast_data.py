from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.schemas.forecast_data import ForecastRequest, ForecastResponse
from app.services import forecast_data_service
from datetime import datetime, timezone
from typing import List
import traceback

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=List[ForecastResponse])
async def get_forecast_data(req: ForecastRequest, db: AsyncSession = Depends(get_db)):
    print(req)
    try:
        # Parse datetime string and make it timezone aware
        parsed_dt = datetime.strptime(req.datetime.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        print(f"ParsedDate: {parsed_dt}")

        # Check if it's not a future datetime
        if parsed_dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Date value should be current or 4 days in future")
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use YYYY-MM-DD HH:00:00")
    
    try:
        unique_traffic_data = list({(item.latitude, item.longitude): item for item in req.traffic_data}.values())
        results = await forecast_data_service.get_forecast_data(db, req.datetime, unique_traffic_data)
        print(f"{len(results)} row(s) returned matching datetime")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching records from the database")
    
    if not results:
        raise HTTPException(status_code=404, detail="No forecast data available for the specified datetime. Possibly forecast API not reached")

    return results