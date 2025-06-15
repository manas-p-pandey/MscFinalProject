from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FastAPI App"
    DATABASE_URL: str
    ENV: str = "development"

    class Config:
        env_file = ".env"
        extra = "forbid"  # default, can use "allow" to silence this error

settings = Settings()