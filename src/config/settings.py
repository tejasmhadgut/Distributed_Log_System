from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    #Database
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # ClickHouse
    CLICKHOUSE_HOST: str = "clickhouse"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_DB: str = "logs_db"

    # JWT 
    JWT_SECRET_KEY: str = "c00428c697d5c22e56712202ac64eaa80812c9f19872146444a8518f56cc1628"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Auth gate set to false to bypass auth during dev)
    AUTH_REQUIRED: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
    

