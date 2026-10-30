from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCS_BUCKET_NAME: str = "motavi-videos"
    # Local dev: path to service-account key file
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # Cloud Run: SA key JSON injected from Secret Manager as env var
    GCP_SERVICE_ACCOUNT_KEY: str = ""
    UPLOAD_PREFIX: str = "uploads/"
    RESULTS_PREFIX: str = "results/"

    # ── Movement classification (analyzer.py) ───────────────────────────────
    # Bending: trunk inclination above this angle (degrees, measured in pixels)
    MOVEMENT_BENDING_DEG: float = 20.0
    # Overhead: a wrist above ear height; margin in normalised image height
    # (positive = the wrist must be this much higher than the ears)
    MOVEMENT_OVERHEAD_MARGIN: float = 0.0
    # Metric "arms above shoulder height": upper arm angle to the trunk
    ARM_ELEVATION_DEG: float = 90.0

    # ── Auth (JWT) ──────────────────────────────────────────────────────────
    # HMAC secret for signing access tokens (inject via Secret Manager).
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    # Bootstrap key required by POST /auth/register to provision users.
    # Empty disables registration entirely.
    SETUP_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
