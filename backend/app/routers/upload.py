"""Video upload in two steps, straight into Cloud Storage (E.3.3).

Cloud Run accepts at most 32 MiB per request; videos are larger. So the
browser uploads to the bucket itself:
  1. POST /upload/session         job (services/jobs.py) and a resumable upload
                                  session for raw/{job_id}/video.mp4
  2. PUT  <upload_url>            browser to Cloud Storage, not this service
  3. POST /upload/{job_id}/start  start the analysis
Customers take the same steps through an upload link (routers/upload_links.py).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from ..config import settings
from ..schemas.upload import ERLAUBTE_TYPEN, Datei, UploadResponse, UploadSessionRequest, UploadSessionResponse
from ..services import analyzer, gcs, jobs
from ..services.workplace.pose_store import PoseRecorder
from .auth import get_current_user, require_job

router = APIRouter()
logger = logging.getLogger(__name__)


def pruefe_datei(datei: Datei) -> str:
    """Content type for the upload session; 422 for other files or too large ones."""
    typ = datei.content_type.lower()
    if typ == "application/octet-stream" and datei.dateiname.lower().endswith((".mp4", ".m4v")):
        typ = "video/mp4"
    if typ not in ERLAUBTE_TYPEN:
        raise HTTPException(status_code=422, detail="Dateityp nicht unterstützt. Erlaubt sind MP4, WebM, MOV und AVI.")
    if datei.groesse_bytes > settings.UPLOAD_MAX_BYTES:
        mb = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
        raise HTTPException(status_code=422, detail=f"Die Datei ist zu groß (höchstens {mb} MB).")
    return typ


def upload_session(job_id: str, datei: Datei, origin: Optional[str]) -> str:
    typ = pruefe_datei(datei)
    try:
        return gcs.create_upload_session(gcs.raw_video_path(job_id), typ, datei.groesse_bytes, origin)
    except Exception:
        logger.exception("Creating the upload session failed: %s", job_id)
        raise HTTPException(status_code=503, detail="Upload derzeit nicht möglich. Bitte später erneut versuchen.")


def analyse_starten(job: dict, background_tasks: BackgroundTasks) -> UploadResponse:
    """Start the analysis once the video is in the bucket; only once per job."""
    job_id = job["job_id"]
    if job.get("status") != jobs.WARTET:
        raise HTTPException(status_code=409, detail="Für diesen Job wurde die Analyse bereits gestartet.")
    if not gcs.blob_exists(gcs.raw_video_path(job_id)):
        raise HTTPException(status_code=409, detail="Das Video ist noch nicht vollständig hochgeladen.")
    job["status"] = jobs.LAEUFT
    job["gestartet_am"] = datetime.now(timezone.utc).isoformat()
    jobs.speichern(job)
    m = job.get("meta", {})
    meta = {
        "company_name": m.get("company_name"),
        "department": m.get("department"),
        "task_description": m.get("task_description"),
        "shift_duration_min": m.get("schichtdauer_min"),
    }
    recorder = PoseRecorder() if settings.WORKPLACE_POSE_RECORDING else None
    background_tasks.add_task(analyzer.run_pipeline, job_id, meta, recorder)
    return UploadResponse(job_id=job_id, status="processing")


@router.post("/upload/session", response_model=UploadSessionResponse, status_code=201)
def create_session(body: UploadSessionRequest, request: Request, user: dict = Depends(get_current_user)) -> UploadSessionResponse:
    pruefe_datei(body)  # before a job is created
    meta = body.model_dump(include={"company_name", "department", "task_description", "schichtdauer_min"})
    try:
        job = jobs.anlegen(user["email"], "intern", meta)
    except Exception:
        logger.exception("Creating the job failed")
        raise HTTPException(status_code=503, detail="Speicher nicht erreichbar.")
    url = upload_session(job["job_id"], body, request.headers.get("origin"))
    return UploadSessionResponse(job_id=job["job_id"], upload_url=url)


@router.post("/upload/{job_id}/start", response_model=UploadResponse, status_code=202)
def start(job_id: str, background_tasks: BackgroundTasks, user: dict = Depends(require_job)) -> UploadResponse:
    job = jobs.laden(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    return analyse_starten(job, background_tasks)
