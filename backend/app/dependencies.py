import json
from functools import lru_cache

from google.cloud import firestore, storage
from google.oauth2 import service_account

from .config import settings


@lru_cache(maxsize=1)
def get_gcs_client() -> storage.Client:
    """Return a cached GCS client.

    Two auth paths:
    - Cloud Run: the attached service account (Application Default
      Credentials, docs/BETRIEB.md); no key needed.
    - Optional: GCP_SERVICE_ACCOUNT_KEY with a key as JSON string, or locally
      GOOGLE_APPLICATION_CREDENTIALS.
    """
    if settings.GCP_SERVICE_ACCOUNT_KEY:
        sa_info = json.loads(settings.GCP_SERVICE_ACCOUNT_KEY)
        creds = service_account.Credentials.from_service_account_info(sa_info)
        return storage.Client(credentials=creds, project=sa_info.get("project_id"))
    return storage.Client()


def get_bucket() -> storage.Bucket:
    return get_gcs_client().bucket(settings.GCS_BUCKET_NAME)


@lru_cache(maxsize=1)
def get_firestore_client() -> firestore.Client:
    """Return a cached Firestore client (same auth paths as GCS)."""
    if settings.GCP_SERVICE_ACCOUNT_KEY:
        sa_info = json.loads(settings.GCP_SERVICE_ACCOUNT_KEY)
        creds = service_account.Credentials.from_service_account_info(sa_info)
        return firestore.Client(credentials=creds, project=sa_info.get("project_id"))
    return firestore.Client()
