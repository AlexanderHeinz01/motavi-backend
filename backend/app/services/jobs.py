"""Jobs and who may see them (E.3.1 of the review on 31.10.2026).

Every job has results/{job_id}/job.json, written before the video is
uploaded: who created it, how (internal upload or upload link for a
customer), the workplace data from the form and the status.

Access: the Motavi team (BERATER_ROLES) sees every job, every other signed-in
user only the jobs they created. Jobs from before job.json existed are only
visible to the team.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from ..config import settings
from . import gcs
from .auth import BERATER_ROLES

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# status values
WARTET = "wartet_auf_upload"
LAEUFT = "processing"
FERTIG = "fertig"
FEHLER = "fehler"


def gueltige_id(job_id: str) -> bool:
    return bool(_UUID.match(job_id or ""))


def job_path(job_id: str) -> str:
    return f"{settings.RESULTS_PREFIX}{job_id}/job.json"


def anlegen(erstellt_von: str, quelle: str, meta: dict, **extra) -> dict:
    """New job waiting for its video. quelle: "intern" or "upload_link"."""
    job = {
        "job_id": str(uuid.uuid4()),
        "erstellt_von": erstellt_von,
        "erstellt_am": datetime.now(timezone.utc).isoformat(),
        "quelle": quelle,
        "status": WARTET,
        "meta": meta,
        **extra,
    }
    gcs.put_json(job_path(job["job_id"]), job)
    return job


def laden(job_id: str) -> Optional[dict]:
    return gcs.get_json(job_path(job_id)) if gueltige_id(job_id) else None


def speichern(job: dict) -> None:
    gcs.put_json(job_path(job["job_id"]), job)


def darf_zugreifen(job: Optional[dict], user: dict) -> bool:
    if user.get("role") in BERATER_ROLES:
        return True
    return bool(job) and job.get("erstellt_von") == user.get("email")


def status_setzen(job_id: str, status: str) -> None:
    """After the analysis (analyzer.py); jobs from before job.json existed have none."""
    job = laden(job_id)
    if job:
        job["status"] = status
        job["beendet_am"] = datetime.now(timezone.utc).isoformat()
        speichern(job)


def liste(user: dict) -> list[dict]:
    """Jobs the user may see, newest first (page Dashboard of the internal tool)."""
    alle = gcs.list_json(f"{settings.RESULTS_PREFIX}*/job.json")
    sichtbar = [j for j in alle if darf_zugreifen(j, user)]
    return sorted(sichtbar, key=lambda j: j.get("erstellt_am", ""), reverse=True)
