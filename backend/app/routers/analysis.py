import io
import logging
import re

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..config import settings
from ..schemas.analysis import (
    ActionItem,
    AnalysisResult,
    ArmsAboveShoulder,
    AnalysisStatusResponse,
    BodyRegions,
    CriticalFrame,
    MovementStats,
    TimelineFrame,
    TimelinePoint,
)
from ..services import auth as auth_svc
from ..services import gcs
from .auth import require_job

router = APIRouter()
logger = logging.getLogger(__name__)

# A frame address works for this many minutes; <img> cannot send the sign-in header
BILD_MINUTEN = 15
_BILD = re.compile(r"^critical_[1-9]\.jpg$")


def _bild_url(job_id: str, gcs_path: str) -> str:
    datei = gcs_path.rsplit("/", 1)[-1]
    token = auth_svc.create_token("bild", BILD_MINUTEN, job=job_id, datei=datei)
    return f"/api/v1/frames/{job_id}/{datei}?t={token}"


@router.get("/analysis/{job_id}", response_model=AnalysisStatusResponse)
def get_analysis(job_id: str, user: dict = Depends(require_job)) -> AnalysisStatusResponse:
    """Poll analysis status.

    Returns:
        - ``{"status": "processing"}`` while the pipeline is running.
        - ``{"status": "done", "result": {...}}`` when complete.
        - ``{"status": "error", "error": "..."}`` on pipeline failure.
    """
    # The raw video exists only while the analysis runs (it is deleted right
    # after), so look for the result first.
    try:
        result_data = gcs.get_result(job_id)
        if result_data is None:
            if gcs.blob_exists(gcs.raw_video_path(job_id)):
                return AnalysisStatusResponse(status="processing")
            raise HTTPException(status_code=404, detail="Job nicht gefunden.")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Reading the result failed: %s", job_id)
        raise HTTPException(status_code=503, detail="Speicher nicht erreichbar.")

    if "error" in result_data:
        return AnalysisStatusResponse(status="error", error=result_data["error"])

    try:
        result = AnalysisResult(
            job_id=result_data["job_id"],
            company_name=result_data.get("company_name"),
            department=result_data.get("department"),
            task_description=result_data.get("task_description"),
            shift_duration_min=result_data["shift_duration_min"],
            erkennung_anteil=result_data.get("erkennung_anteil"),
            reba_score=result_data["reba_score"],
            reba_level=result_data["reba_level"],
            body_regions=BodyRegions(**result_data["body_regions"]),
            movements={k: MovementStats(**v) for k, v in result_data["movements"].items()},
            arms_above_shoulder=(
                ArmsAboveShoulder(**result_data["arms_above_shoulder"])
                if result_data.get("arms_above_shoulder") else None
            ),
            timeline=[TimelinePoint(**p) for p in result_data["timeline"]],
            timeline_frames=[TimelineFrame(**p) for p in result_data.get("timeline_frames", [])],
            critical_frames=[
                CriticalFrame(**c, bild_url=_bild_url(job_id, c["gcs_path"]))
                for c in result_data.get("critical_frames", [])
            ],
            action_items=[ActionItem(priority=a["priority"], region=a["region"], text=a["text"]) for a in result_data["action_items"]],
        )
    except Exception:
        logger.exception("Parsing the result failed: %s", job_id)
        return AnalysisStatusResponse(status="error", error="Das Ergebnis konnte nicht gelesen werden.")

    return AnalysisStatusResponse(status="done", result=result)


@router.get("/frames/{job_id}/{filename}")
def get_frame(job_id: str, filename: str, t: str = Query(...)) -> StreamingResponse:
    """Serve a critical frame JPEG; t is the short-lived token from get_analysis."""
    try:
        payload = auth_svc.decode_token(t, "bild")
    except jwt.PyJWTError:
        raise HTTPException(status_code=403, detail="Der Bildlink ist abgelaufen.")
    if payload.get("job") != job_id or payload.get("datei") != filename or not _BILD.match(filename):
        raise HTTPException(status_code=403, detail="Der Bildlink ist ungültig.")
    gcs_path = f"{settings.RESULTS_PREFIX}{job_id}/frames/{filename}"
    try:
        data = gcs.download_bytes(gcs_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Bild nicht gefunden.")
    return StreamingResponse(io.BytesIO(data), media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
