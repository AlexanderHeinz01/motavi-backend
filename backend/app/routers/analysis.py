# TODO: implement in Step 2
from fastapi import APIRouter

from ..schemas.analysis import AnalysisStatusResponse

router = APIRouter()


@router.get("/analysis/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis(job_id: str) -> AnalysisStatusResponse:
    """Poll analysis status. Returns processing|done with result when ready."""
    # TODO: implement
    raise NotImplementedError
