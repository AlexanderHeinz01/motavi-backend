import io
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..services import gcs, pdf
from .auth import require_job

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/report/{job_id}/pdf")
def get_report_pdf(job_id: str, user: dict = Depends(require_job)) -> StreamingResponse:
    """Generate and stream the 4-page ergonomics report of a completed analysis."""
    result_data = gcs.get_result(job_id)
    if result_data is None:
        raise HTTPException(status_code=404, detail="Kein Ergebnis vorhanden. Die Analyse läuft möglicherweise noch.")
    if "error" in result_data:
        raise HTTPException(status_code=422, detail="Die Analyse ist mit einem Fehler beendet worden.")

    try:
        pdf_bytes = pdf.generate_report_pdf(result_data)
    except Exception:
        logger.exception("PDF generation failed: %s", job_id)
        raise HTTPException(status_code=500, detail="Der Report konnte nicht erstellt werden.")

    filename = f"motavi-report-{job_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
