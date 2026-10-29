import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..schemas.analysis import (
    ActionItem,
    AnalysisResult,
    AnalysisStatusResponse,
    BodyRegions,
    CriticalFrame,
    MovementStats,
    TimelineFrame,
    TimelinePoint,
)
from ..services import gcs
from ..config import settings

router = APIRouter()


@router.get("/analysis/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis(job_id: str) -> AnalysisStatusResponse:
    """Poll analysis status.

    Returns:
        - ``{"status": "processing"}`` while the pipeline is running.
        - ``{"status": "done", "result": {...}}`` when complete.
        - ``{"status": "error", "error": "..."}`` on pipeline failure.
    """
    upload_path = f"{settings.UPLOAD_PREFIX}{job_id}/video.mp4"
    try:
        exists = gcs.blob_exists(upload_path)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"GCS unavailable: {exc}") from exc

    if not exists:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")

    result_data = gcs.get_result(job_id)
    if result_data is None:
        return AnalysisStatusResponse(status="processing")

    if "error" in result_data:
        return AnalysisStatusResponse(status="error", error=result_data["error"])

    try:
        result = AnalysisResult(
            job_id=result_data["job_id"],
            company_name=result_data.get("company_name"),
            department=result_data.get("department"),
            task_description=result_data.get("task_description"),
            worker_height_cm=result_data.get("worker_height_cm"),
            shift_duration_min=result_data["shift_duration_min"],
            reba_score=result_data["reba_score"],
            reba_level=result_data["reba_level"],
            body_regions=BodyRegions(**result_data["body_regions"]),
            movements={k: MovementStats(**v) for k, v in result_data["movements"].items()},
            timeline=[TimelinePoint(**p) for p in result_data["timeline"]],
            timeline_frames=[TimelineFrame(**p) for p in result_data.get("timeline_frames", [])],
            critical_frames=[CriticalFrame(**c) for c in result_data.get("critical_frames", [])],
            action_items=[ActionItem(**a) for a in result_data["action_items"]],
        )
    except Exception as exc:
        return AnalysisStatusResponse(status="error", error=f"Result parse error: {exc}")

    return AnalysisStatusResponse(status="done", result=result)


@router.get("/frames/{job_id}/{filename}")
async def get_frame(job_id: str, filename: str) -> StreamingResponse:
    """Serve a critical frame JPEG from GCS."""
    gcs_path = f"{settings.RESULTS_PREFIX}{job_id}/frames/{filename}"
    try:
        data = gcs.download_bytes(gcs_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Frame not found.")
    return StreamingResponse(io.BytesIO(data), media_type="image/jpeg")
