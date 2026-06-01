from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gemini_api_key: str
    environment: str = "development"

    class Config:
        env_file = ".env"

# Single instance imported everywhere
settings = Settings()