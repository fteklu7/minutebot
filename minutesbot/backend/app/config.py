from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./minutesbot.db"

    # leave blank to run in offline mode (fake AI, text uploads only)
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embed_model: str = "text-embedding-3-small"
    transcribe_model: str = "whisper-1"

    # blank = no auth (local dev only). set it if you deploy, so nobody else
    # can upload files and run up your OpenAI bill
    access_key: str = ""

    max_upload_mb: int = 25  # whisper api limit

    cors_origins: str = "http://localhost:5173"


settings = Settings()
