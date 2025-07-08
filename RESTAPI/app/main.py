from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import user
from app.api.routes import logs
from app.api.routes import site
from app.core.database import sync_engine, Base

app = FastAPI(title=settings.APP_NAME)

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=sync_engine)

app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(logs.router, prefix="/logs", tags=["Logs"])
app.include_router(site.router, prefix="/sites", tags=["Sites"])
