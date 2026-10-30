import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..config import settings
from ..schemas.upload import UploadResponse
from ..services import analyzer, gcs
from ..services.workplace.pose_store import PoseRecorder

router = APIRouter()

_ALLOWED_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "application/octet-stream",  # some browsers send this for binary uploads
}
_MAX_BYTES = 500 * 1024 * 1024  # 500 MB


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_name: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    task_description: Optional[str] = Form(None),
    shift_duration_min: int = Form(480),
    worker_height_cm: Optional[int] = Form(None),
) -> UploadResponse:
    """Accept a video file, store it in GCS, and trigger the analysis pipeline."""
    if file.content_type and file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {file.content_type}. "
                   "Accepted: mp4, webm, mov, avi.",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Empty file.")
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=422, detail="File too large (max 500 MB).")

    job_id = str(uuid.uuid4())

    try:
        gcs.upload_video(job_id, data, file.content_type or "video/mp4")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"GCS upload failed: {exc}") from exc

    meta = {
        "company_name":       company_name,
        "department":         department,
        "task_description":   task_description,
        "shift_duration_min": shift_duration_min,
        "worker_height_cm":   worker_height_cm,
    }
    recorder = PoseRecorder() if settings.WORKPLACE_POSE_RECORDING else None
    background_tasks.add_task(analyzer.run_pipeline, job_id, meta, recorder)

    return UploadResponse(job_id=job_id, status="processing")
