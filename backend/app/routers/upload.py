# TODO: implement in Step 2
from fastapi import APIRouter, BackgroundTasks, File, UploadFile

from ..schemas.upload import UploadResponse

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Accept video upload, store to GCS, trigger analysis pipeline."""
    # TODO: implement
    raise NotImplementedError
