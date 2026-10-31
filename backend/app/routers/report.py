import io
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..config import settings
from ..services import gcs, pdf
from ..services.workplace.cycles import detect_cycles
from ..services.workplace.pose_store import load_npz
from ..services.workplace.preprocess import prepare
from ..services.workplace.reach import ZONEN_TEXT, analyse_reach
from .auth import require_job

router = APIRouter()
logger = logging.getLogger(__name__)


def ablauf_kennzahlen(job_id: str, shift_min: float) -> dict | None:
    """Cycle time and reach from pose.npz for the report; None when the pose
    data are gone (after 30 days) or cannot be read."""
    try:
        data = gcs.download_bytes(f"{settings.RESULTS_PREFIX}{job_id}/pose.npz")
    except FileNotFoundError:
        return None
    try:
        prep = prepare(load_npz(data))
        zyklen = detect_cycles(prep, shift_min)
        greifraum = analyse_reach(prep)
    except Exception:
        logger.exception("Cycle and reach values for the report failed: %s", job_id)
        return None
    return {
        "zykluszeit_s": zyklen.zykluszeit_median.wert,
        "zyklen_pro_schicht": zyklen.zyklen_pro_schicht.wert,
        "hinweis": None if zyklen.erkannt else zyklen.hinweis,
        "griffe_ausserhalb": greifraum.griffe_ausserhalb.wert,
        "hoehenzonen": {k: v.wert for k, v in greifraum.hoehenzonen.items()},
        "zonen_text": ZONEN_TEXT,
    }


@router.get("/report/{job_id}/pdf")
def get_report_pdf(job_id: str, user: dict = Depends(require_job)) -> StreamingResponse:
    """Generate and stream the 4-page ergonomics report of a completed analysis."""
    result_data = gcs.get_result(job_id)
    if result_data is None:
        raise HTTPException(status_code=404, detail="Kein Ergebnis vorhanden. Die Analyse läuft möglicherweise noch.")
    if "error" in result_data:
        raise HTTPException(status_code=422, detail="Die Analyse ist mit einem Fehler beendet worden.")

    ablauf = ablauf_kennzahlen(job_id, float(result_data.get("shift_duration_min") or 450))
    try:
        pdf_bytes = pdf.generate_report_pdf(result_data, ablauf)
    except Exception:
        logger.exception("PDF generation failed: %s", job_id)
        raise HTTPException(status_code=500, detail="Der Report konnte nicht erstellt werden.")

    filename = f"motavi-report-{job_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
