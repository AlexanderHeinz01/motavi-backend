from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # "production" on Cloud Run (cloudbuild.yaml): checks at start, see main.py
    APP_ENV: str = "dev"
    # Origins allowed to call the API from a browser
    # (the website for the contact form), separated by ",". Empty: every origin
    # (development only; production refuses to start, main.py).
    CORS_ORIGINS: str = ""
    GCS_BUCKET_NAME: str = "motavi-videos"
    # Local dev: path to service-account key file
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    # Optional SA key JSON. On Cloud Run the attached service account is used
    # instead (docs/BETRIEB.md); leave empty there.
    GCP_SERVICE_ACCOUNT_KEY: str = ""
    # Raw video: deleted right after the analysis, lifecycle 1 day as a
    # safety net (docs/LOESCHKONZEPT.md). Before 30.10.2026 raw videos were
    # stored under uploads/.
    RAW_PREFIX: str = "raw/"
    RESULTS_PREFIX: str = "results/"

    # ── Upload (routers/upload.py, routers/upload_links.py) ────────────────
    # Largest video; the analysis keeps it in /tmp, which is memory on Cloud Run
    UPLOAD_MAX_BYTES: int = 1024 * 1024 * 1024
    # Upload links for customers: validity in days
    UPLOAD_LINK_DAYS: int = 14
    # Public address of this service, used to build upload links
    # (e.g. https://app.example.de); empty gives a relative link
    PUBLIC_APP_URL: str = ""

    # ── Analysis (analyzer.py) ──────────────────────────────────────────────
    # Model files; the Docker image contains them here
    MODEL_DIR: str = "/tmp/motavi-models"
    # Below this share of sampled frames with a person the analysis ends with
    # an error instead of a result (E.3.5)
    ANALYSE_MIN_ERKENNUNG: float = 0.5

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
    # Proxies in front of the service that append to X-Forwarded-For:
    # 1 for Cloud Run directly, 2 behind an external load balancer
    CONTACT_PROXY_HOPS: int = 1
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
        # .env may also hold values for other tools (e.g. VITE_API_BASE_URL)
        extra = "ignore"


settings = Settings()
