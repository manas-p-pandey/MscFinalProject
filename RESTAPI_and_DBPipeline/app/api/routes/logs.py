from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.User_Logs import UserLogEntry, UserLogOut
from app.services.log_service import create_user_logs
from app.core.database import SessionLocal

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=UserLogOut)
async def create_user_logs_api(user: UserLogEntry, db: AsyncSession = Depends(get_db)):
    return await create_user_logs(db, user)