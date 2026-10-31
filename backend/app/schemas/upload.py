from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Accepted video types; the raw video is stored as raw/{job_id}/video.mp4
ERLAUBTE_TYPEN = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}


class Arbeitsplatz(BaseModel):
    """Workplace data of a job (no person)."""
    model_config = ConfigDict(extra="forbid")

    company_name: Optional[str] = Field(None, max_length=120)
    department: Optional[str] = Field(None, max_length=120)
    task_description: Optional[str] = Field(None, max_length=200)
    # Net working time per shift without breaks (decision P9 on 31.10.2026)
    schichtdauer_min: int = Field(450, ge=60, le=720)


class Datei(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dateiname: str = Field(..., min_length=1, max_length=200)
    groesse_bytes: int = Field(..., gt=0)
    content_type: str = Field(..., max_length=100)


class UploadSessionRequest(Arbeitsplatz, Datei):
    pass


class UploadSessionResponse(BaseModel):
    job_id: str
    upload_url: str


class UploadResponse(BaseModel):
    job_id: str
    status: str  # "processing"


class UploadLinkRequest(Arbeitsplatz):
    gueltig_tage: Optional[int] = Field(None, ge=1, le=60)


class UploadLinkResponse(BaseModel):
    job_id: str
    url: str
    gueltig_bis: str


class UploadLinkInfo(BaseModel):
    arbeitsplatz: Optional[str]
    schichtdauer_min: int
    gueltig_bis: str
    max_bytes: int
