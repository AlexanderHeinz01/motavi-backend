from functools import lru_cache
from google.cloud import storage
from .config import settings


@lru_cache(maxsize=1)
def get_gcs_client() -> storage.Client:
    return storage.Client()


def get_bucket() -> storage.Bucket:
    client = get_gcs_client()
    return client.bucket(settings.GCS_BUCKET_NAME)
