from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCS_BUCKET_NAME: str = "motavi-videos"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    UPLOAD_PREFIX: str = "uploads/"
    RESULTS_PREFIX: str = "results/"

    class Config:
        env_file = ".env"


settings = Settings()
