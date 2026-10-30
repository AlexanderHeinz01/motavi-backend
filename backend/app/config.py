from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GCS_BUCKET_NAME: str = "motavi-videos"
    # Local dev: path to service-account key file
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # Cloud Run: SA key JSON injected from Secret Manager as env var
    GCP_SERVICE_ACCOUNT_KEY: str = ""
    # Raw video: deleted right after the analysis, lifecycle 1 day as a
    # safety net (docs/LOESCHKONZEPT.md). Before 30.10.2026 raw videos were
    # stored under uploads/.
    RAW_PREFIX: str = "raw/"
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

    # ── Contact form of the website (POST /api/v1/contact, docs/KONTAKT.md) ──
    # Requests per client IP within the window
    CONTACT_RATE_LIMIT: int = 5
    CONTACT_RATE_WINDOW_S: int = 600
    # Requests are deleted after this many days (Firestore TTL on loeschen_am)
    CONTACT_RETENTION_DAYS: int = 365
    # Optional e-mail notification; empty SMTP_HOST disables it
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    CONTACT_NOTIFY_TO: str = ""

    # ── Steckbrief module ───────────────────────────────────────────────────
    # Keep per-frame pose data (results/{job_id}/pose.npz, docs/POSE_DATEN.md)
    WORKPLACE_POSE_RECORDING: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
