from pydantic_settings import BaseSettings
from os import getenv

HRMIS_API_URL = getenv("HRMIS_API_URL", "http://localhost:3005")
HRMIS_API_TOKEN = getenv("HRMIS_API_TOKEN", "your_default_token_here")
DATABASE_URL = getenv("DATABASE_URL", "mysql+pymysql://root:5lsolutions101520@localhost:3306/assistant_hrmis")

class Settings(BaseSettings):
    GROQ_API_KEY: str | None = None
    HF_API_KEY: str | None = None 
    HRMIS_API_URL: str = HRMIS_API_URL
    HRMIS_API_TOKEN: str = HRMIS_API_TOKEN
    DATABASE_URL: str = DATABASE_URL
    
    class Config:
        env_file = ".env"

settings = Settings()
