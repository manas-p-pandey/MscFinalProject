from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.User_Details import UserRegistration, UserOut
from app.services.user_service import create_user
from app.core.database import SessionLocal

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=UserOut)
async def create_user_api(user: UserRegistration, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)
