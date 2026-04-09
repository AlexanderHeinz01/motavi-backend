# TODO: implement in Step 2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/report/{job_id}/pdf")
async def get_report_pdf(job_id: str) -> StreamingResponse:
    """Generate and stream PDF report for a completed analysis."""
    # TODO: implement
    raise NotImplementedError
