from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate, UserOut
from app.services.user_service import create_user
from app.core.database import SessionLocal

router = APIRouter()

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/", response_model=UserOut)
async def create_user_api(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user)
