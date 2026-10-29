"""GCS I/O helpers — upload, download, existence checks."""
import io
import json
from typing import Optional

from ..config import settings
from ..dependencies import get_bucket


def upload_video(job_id: str, data: bytes, content_type: str = "video/mp4") -> str:
    """Upload raw video bytes. Returns the GCS blob path."""
    path = f"{settings.UPLOAD_PREFIX}{job_id}/video.mp4"
    _upload(path, data, content_type)
    return path


def upload_bytes(path: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload arbitrary bytes to an explicit GCS path."""
    _upload(path, data, content_type)


def _upload(path: str, data: bytes, content_type: str) -> None:
    blob = get_bucket().blob(path)
    blob.upload_from_file(io.BytesIO(data), content_type=content_type)


def download_bytes(path: str) -> bytes:
    """Download a blob as bytes. Raises FileNotFoundError if absent."""
    blob = get_bucket().blob(path)
    if not blob.exists():
        raise FileNotFoundError(f"GCS blob not found: {path}")
    return blob.download_as_bytes()


def get_result(job_id: str) -> Optional[dict]:
    """Return parsed result JSON for *job_id*, or None if not yet written."""
    path = f"{settings.RESULTS_PREFIX}{job_id}/result.json"
    blob = get_bucket().blob(path)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_bytes())


def blob_exists(path: str) -> bool:
    """Return True if the GCS blob exists."""
    return get_bucket().blob(path).exists()
