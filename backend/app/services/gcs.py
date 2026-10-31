"""GCS I/O helpers — upload, download, existence checks."""
import io
import json
from typing import Optional

from ..config import settings
from ..dependencies import get_bucket


def raw_video_path(job_id: str) -> str:
    """Raw (not anonymised) video of a job; deleted right after the analysis."""
    return f"{settings.RAW_PREFIX}{job_id}/video.mp4"


def create_upload_session(path: str, content_type: str, size: int, origin: Optional[str]) -> str:
    """Resumable upload session for *path*; the browser sends the file to the
    returned URL directly (Cloud Run allows at most 32 MiB per request).
    origin: the page that uploads; Cloud Storage answers CORS for it."""
    blob = get_bucket().blob(path)
    return blob.create_resumable_upload_session(content_type=content_type, size=size, origin=origin)


def download_to_file(path: str, dest: str) -> None:
    """Download a blob into a local file. Raises FileNotFoundError if absent."""
    blob = get_bucket().blob(path)
    if not blob.exists():
        raise FileNotFoundError(f"GCS blob not found: {path}")
    blob.download_to_filename(dest)


def upload_video(job_id: str, data: bytes, content_type: str = "video/mp4") -> str:
    """Upload raw video bytes. Returns the GCS blob path."""
    path = raw_video_path(job_id)
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


def get_json(path: str) -> Optional[dict]:
    """Parsed JSON blob, or None if it does not exist."""
    blob = get_bucket().blob(path)
    if not blob.exists():
        return None
    return json.loads(blob.download_as_bytes())


def put_json(path: str, data: dict) -> None:
    _upload(path, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json")


def blob_exists(path: str) -> bool:
    """Return True if the GCS blob exists."""
    return get_bucket().blob(path).exists()


def delete_blob(path: str) -> bool:
    """Delete a blob. Returns False if it did not exist."""
    blob = get_bucket().blob(path)
    if not blob.exists():
        return False
    blob.delete()
    return True
