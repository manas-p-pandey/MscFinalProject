from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FastAPI App"
    DATABASE_URL: str
    ENV: str = "development"  # 👈 Add this line

    class Config:
        env_file = ".env"
        extra = "forbid"

settings = Settings()
