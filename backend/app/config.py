from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCS_BUCKET_NAME: str = "motavi-videos"
    # Local dev: path to service-account key file
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # Cloud Run: SA key JSON injected from Secret Manager as env var
    GCP_SERVICE_ACCOUNT_KEY: str = ""
    UPLOAD_PREFIX: str = "uploads/"
    RESULTS_PREFIX: str = "results/"

    class Config:
        env_file = ".env"


settings = Settings()
