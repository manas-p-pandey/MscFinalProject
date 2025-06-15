from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import user
from app.core.database import engine, Base

app = FastAPI(title=settings.APP_NAME)

app.include_router(user.router, prefix="/users", tags=["Users"])
