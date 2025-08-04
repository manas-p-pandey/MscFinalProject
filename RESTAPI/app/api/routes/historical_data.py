from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal
from app.schemas.historical_data import Historical_Data
from app.services.historical_data_service import historical_service
from datetime import datetime, timedelta, timezone
from typing import List
import traceback

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/", response_model=List[Historical_Data])
async def read_records_by_datetime(
    datetime_value: str = Query(..., description="Datetime string in format YYYY-MM-DD HH:00:00"),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Parse datetime string and make it timezone aware
        parsed_dt = datetime.strptime(datetime_value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        print(f"ParsedDate: {parsed_dt}")

        # Check if it's not a future datetime
        if parsed_dt >= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Date value should be before today's date")
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use YYYY-MM-DD HH:00:00")

    try:
        matching_records = await historical_service(db, datetime.strptime(datetime_value, "%Y-%m-%d %H:%M:%S"))
        print(f"{len(matching_records)} row(s) returned matching datetime")
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error fetching records from the database")

    if not matching_records:
        raise HTTPException(status_code=404, detail="Record not found for the given datetime")

    return matching_records
