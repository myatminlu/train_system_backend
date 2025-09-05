from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    PGHOST: str
    PGDATABASE: str
    PGUSER: str
    PGPASSWORD: str
    PGSSLMODE: str = "require"
    PGCHANNELBINDING: str = "require"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    PROJECT_NAME: str = "Bangkok Train Transport System"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.PGUSER}:{self.PGPASSWORD}@{self.PGHOST}/{self.PGDATABASE}?sslmode={self.PGSSLMODE}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()