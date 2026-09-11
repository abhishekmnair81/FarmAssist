from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    OPENWA_API_URL: str
    OPENWA_API_KEY: str = ""
    OPENWA_SESSION_ID: str = "default"
    DEFAULT_LAT: float = 20.5937
    DEFAULT_LON: float = 78.9629
    DEFAULT_VOICE: str = "en-IN-NeerjaNeural"
    WHITELISTED_NUMBERS: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
