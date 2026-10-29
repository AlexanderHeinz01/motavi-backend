import io

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..services import gcs, pdf

router = APIRouter()


@router.get("/report/{job_id}/pdf")
async def get_report_pdf(job_id: str) -> StreamingResponse:
    """Generate and stream a 4-page PDF report for a completed analysis."""
    result_data = gcs.get_result(job_id)
    if result_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No result found for job {job_id!r}. Analysis may still be running.",
        )
    if "error" in result_data:
        raise HTTPException(
            status_code=422,
            detail=f"Job {job_id!r} ended with an error: {result_data['error']}",
        )

    try:
        pdf_bytes = pdf.generate_report_pdf(result_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

    filename = f"motavi-report-{job_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
