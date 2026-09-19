import os
from pydantic_settings import BaseSettings

# Base data directory relative to project root
DEFAULT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

class Settings(BaseSettings):
    GROQ_API_KEY: str
    OPENWA_API_URL: str
    OPENWA_API_KEY: str = ""
    OPENWA_SESSION_ID: str = "default"
    DEFAULT_LAT: float = 20.5937
    DEFAULT_LON: float = 78.9629
    DEFAULT_VOICE: str = "en-IN-NeerjaNeural"
    WHITELISTED_NUMBERS: str = ""

    LLM_MODEL: str = "openai/gpt-oss-120b"
    DB_PATH: str = os.path.join(DEFAULT_DATA_DIR, "checkpoints.sqlite")
    LOCATIONS_DB_PATH: str = os.path.join(DEFAULT_DATA_DIR, "locations.json")
    SESSION_TTL_SECONDS: int = 86400  # 24 hours (expanded from 3 mins)
    ALLOW_GROUP_MESSAGES: bool = False  # By default, only respond to 1-on-1 direct messages (DMs)

    NVIDIA_API_KEY: str = ""
    NVDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "openai/gpt-oss-20b"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def effective_nvidia_api_key(self) -> str:
        return self.NVIDIA_API_KEY or self.NVDIA_API_KEY

settings = Settings()
DB_PATH = settings.DB_PATH
