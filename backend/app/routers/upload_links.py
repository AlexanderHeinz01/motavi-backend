"""Upload links for customers (decision G2 on 31.10.2026).

There is no customer self-service. The Motavi team creates a link per
workplace; the customer opens it, uploads the video and the analysis starts.
The link carries a signed token (typ "upload", services/auth.py) with the job
id and an expiry. It works until the video has been handed over.

POST /upload-links                   create (Motavi team)
GET  /upload-links/{token}           workplace, valid until (public)
POST /upload-links/{token}/session   resumable upload session (public)
POST /upload-links/{token}/start     start the analysis (public)
"""
import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from ..config import settings
from ..schemas.upload import Datei, UploadLinkInfo, UploadLinkRequest, UploadLinkResponse, UploadResponse
from ..services import auth as auth_svc
from ..services import jobs
from .auth import _require_config, require_berater
from .upload import analyse_starten, upload_session

router = APIRouter()
logger = logging.getLogger(__name__)


def _job_aus_token(token: str) -> tuple[dict, datetime]:
    """Job and expiry of a valid link; 410 when expired or used, 404 otherwise."""
    _require_config()
    try:
        payload = auth_svc.decode_token(token, "upload")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=410, detail="Der Link ist abgelaufen. Bitte fordern Sie einen neuen an.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=404, detail="Der Link ist ungültig.")
    try:
        job = jobs.laden(payload.get("job", ""))
    except Exception:
        logger.exception("Loading the job of an upload link failed")
        raise HTTPException(status_code=503, detail="Upload derzeit nicht möglich. Bitte später erneut versuchen.")
    if not job or job.get("quelle") != "upload_link":
        raise HTTPException(status_code=404, detail="Der Link ist ungültig.")
    if job.get("status") != jobs.WARTET:
        raise HTTPException(status_code=410, detail="Für diesen Link wurde bereits ein Video übermittelt.")
    return job, datetime.fromtimestamp(payload["exp"], tz=timezone.utc)


def _arbeitsplatz(meta: dict) -> str | None:
    teile = [meta.get(k) for k in ("department", "task_description") if meta.get(k)]
    return " · ".join(teile) or None


@router.post("/upload-links", response_model=UploadLinkResponse, status_code=201)
def create_link(body: UploadLinkRequest, user: dict = Depends(require_berater)) -> UploadLinkResponse:
    tage = body.gueltig_tage or settings.UPLOAD_LINK_DAYS
    meta = body.model_dump(include={"company_name", "department", "task_description", "schichtdauer_min"})
    gueltig_bis = datetime.now(timezone.utc) + timedelta(days=tage)
    try:
        job = jobs.anlegen(user["email"], "upload_link", meta, link_gueltig_bis=gueltig_bis.isoformat())
    except Exception:
        logger.exception("Creating the job for an upload link failed")
        raise HTTPException(status_code=503, detail="Speicher nicht erreichbar.")
    token = auth_svc.create_token("upload", tage * 24 * 60, job=job["job_id"])
    url = f"{settings.PUBLIC_APP_URL.rstrip('/')}/hochladen/{token}"
    return UploadLinkResponse(job_id=job["job_id"], url=url, gueltig_bis=gueltig_bis.isoformat())


@router.get("/upload-links/{token}", response_model=UploadLinkInfo)
def link_info(token: str) -> UploadLinkInfo:
    job, gueltig_bis = _job_aus_token(token)
    meta = job.get("meta", {})
    return UploadLinkInfo(
        arbeitsplatz=_arbeitsplatz(meta),
        schichtdauer_min=meta.get("schichtdauer_min", 450),
        gueltig_bis=gueltig_bis.isoformat(),
        max_bytes=settings.UPLOAD_MAX_BYTES,
    )


@router.post("/upload-links/{token}/session")
def link_session(token: str, body: Datei, request: Request) -> dict:
    job, _ = _job_aus_token(token)
    return {"upload_url": upload_session(job["job_id"], body, request.headers.get("origin"))}


@router.post("/upload-links/{token}/start", response_model=UploadResponse, status_code=202)
def link_start(token: str, background_tasks: BackgroundTasks) -> UploadResponse:
    job, _ = _job_aus_token(token)
    analyse_starten(job, background_tasks)
    # the customer gets no job id: results are for the Motavi team
    return UploadResponse(job_id="", status="processing")
