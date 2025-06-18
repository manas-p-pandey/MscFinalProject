from sqlalchemy.ext.asyncio import AsyncSession
from app.models.User_Details import User_Details
from app.schemas.User_Details import UserRegistration

async def create_user(db: AsyncSession, user: UserRegistration):
    existing = await db.execute(
        db.select(User_Details).filter(User_Details.Email == user.Email)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User_Details(**user.dict(), Approved=False)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user