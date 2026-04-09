"""MediaPipe REBA analysis pipeline (runs as FastAPI BackgroundTask).

Pipeline steps:
1. Download raw video from GCS (uploads/{job_id}/video.mp4)
2. Anonymize: detect person via MediaPipe Pose, fill head bbox
   (top 38% of person height + 20 px padding) with opaque grey rect
3. REBA scoring per frame using landmark angle calculations
4. Aggregate results: timeline, movement classifications, body region
   subscores, action items
5. Write results/{job_id}/result.json to GCS
"""
# TODO: implement in Step 2


async def run_pipeline(job_id: str) -> None:
    """BackgroundTask entry point: anonymize video and run REBA analysis."""
    # TODO: implement
    raise NotImplementedError
