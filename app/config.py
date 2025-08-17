from pydantic_settings import BaseSettings
from os import getenv

HRMIS_API_URL = getenv("HRMIS_API_URL", "http://localhost:3005")
HRMIS_API_TOKEN = getenv("HRMIS_API_TOKEN", "your_default_token_here")

class Settings(BaseSettings):
    GROQ_API_KEY: str | None = None
    HF_API_KEY: str | None = None 
    HRMIS_API_URL: str = HRMIS_API_URL
    HRMIS_API_TOKEN: str = HRMIS_API_TOKEN

    class Config:
        env_file = ".env"

settings = Settings()
