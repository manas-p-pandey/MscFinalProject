from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.schemas.forecast_data import Forecast_Data
from app.services.forecast_data_service import forecast_service
from datetime import datetime
from typing import List

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=List[Forecast_Data])
async def read_records_by_datetime(
    datetime_value: str = Query(..., description="Datetime string in format YYYY-MM-DD HH:00:00"),
    db: AsyncSession = Depends(get_db)
):
    try:
        parsed_dt = datetime.strptime(datetime_value, "%Y-%m-%d %H:%M:%S")        
        print(f"ParsedDate: {parsed_dt}")
        if parsed_dt.date() < datetime.now().date():
            raise HTTPException(status_code=401, detail="Date value should be on or after today's date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use YYYY-MM-DD HH:00:00")

    matching_records = await forecast_service(db, parsed_dt)
    print(f"{len(matching_records)} row(s) returned matching forecast datetime")

    if not matching_records:
        raise HTTPException(status_code=404, detail="Forecast not found for the given datetime")

    return matching_records
