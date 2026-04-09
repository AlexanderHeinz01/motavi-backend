"""GCS upload/download/exists helpers."""
# TODO: implement in Step 2
import json
from typing import Optional

from ..config import settings
from ..dependencies import get_bucket


def upload_video(job_id: str, data: bytes) -> str:
    """Upload raw video bytes to GCS. Returns GCS blob path."""
    # TODO: implement
    raise NotImplementedError


def upload_bytes(path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload arbitrary bytes to a GCS path."""
    # TODO: implement
    raise NotImplementedError


def download_bytes(path: str) -> bytes:
    """Download blob as bytes. Raises FileNotFoundError if missing."""
    # TODO: implement
    raise NotImplementedError


def get_result(job_id: str) -> Optional[dict]:
    """Download result JSON from GCS. Returns None if not yet present."""
    # TODO: implement
    raise NotImplementedError


def blob_exists(path: str) -> bool:
    """Check whether a GCS blob exists."""
    # TODO: implement
    raise NotImplementedError
