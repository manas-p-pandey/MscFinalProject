from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import SessionLocal

from RESTAPI.app.schemas.lstm_stats import UserRegistration, UserOut
from RESTAPI.app.services.dashboard_service import create_user

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=UserOut)
async def create_user_api(user: UserRegistration, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)
