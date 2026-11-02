"""GET /jobs: overview of the jobs for the page Dashboard of the internal tool.

The Motavi team sees every job, others only their own (services/jobs.py).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from ..services import jobs
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _arbeitsplatz(meta: dict) -> str | None:
    teile = [meta.get(k) for k in ("department", "task_description") if meta.get(k)]
    return " · ".join(teile) or None


@router.get("/jobs")
def liste(user: dict = Depends(get_current_user)) -> list[dict]:
    try:
        alle = jobs.liste(user)
    except Exception:
        logger.exception("Listing the jobs failed")
        raise HTTPException(status_code=503, detail="Speicher nicht erreichbar.")
    return [
        {
            "job_id": j["job_id"],
            "erstellt_am": j.get("erstellt_am"),
            "erstellt_von": j.get("erstellt_von"),
            "quelle": j.get("quelle"),
            "status": j.get("status"),
            "arbeitsplatz": _arbeitsplatz(j.get("meta", {})),
            "unternehmen": j.get("meta", {}).get("company_name"),
            "link_gueltig_bis": j.get("link_gueltig_bis"),
        }
        for j in alle
    ]
