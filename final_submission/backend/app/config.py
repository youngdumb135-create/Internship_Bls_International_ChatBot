# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages application settings, automatically loading from environment 
    variables and a .env file.
    """
    DB_PATH: str
    OLLAMA_MODEL: str
    LLM_MODEL: str
    K_DOCS: int = 3 # Optional: Provide a default value if not in .env

    # This configuration tells Pydantic to look for a .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Create a single, global instance of the settings to be used throughout the app
settings = Settings()



# in main file 
# from .config import settings
# and change everywhere settings.k_docs etc
