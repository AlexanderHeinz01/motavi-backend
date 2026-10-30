from typing import Dict, List, Optional

from pydantic import BaseModel


class BodyRegions(BaseModel):
    lumbar: float
    shoulder_l: float
    shoulder_r: float
    neck: float
    knee_l: float
    knee_r: float
    forearm: float


class MovementStats(BaseModel):
    pct: float
    minutes: float


class ArmsAboveShoulder(BaseModel):
    threshold_deg: float
    pct: float
    minutes: float
    max_deg: float


class TimelinePoint(BaseModel):
    minute: int
    reba: float


class TimelineFrame(BaseModel):
    second: float
    movement: str  # "neutral" | "bending" | "overhead"


class CriticalFrame(BaseModel):
    rank: int
    second: float
    reba: float
    movement: str
    gcs_path: str


class ActionItem(BaseModel):
    priority: str  # "CRITICAL" | "MEDIUM"
    region: str
    text: str
    reduction_pct: Optional[int] = None


class AnalysisResult(BaseModel):
    job_id: str
    worker_id: Optional[str] = None
    company_name: Optional[str] = None
    department: Optional[str] = None
    task_description: Optional[str] = None
    worker_height_cm: Optional[int] = None
    shift_duration_min: int
    reba_score: float
    reba_level: str  # "LOW" | "MEDIUM" | "HIGH" | "VERY_HIGH"
    body_regions: BodyRegions
    movements: Dict[str, MovementStats]
    # Own metric, not yet a class in the dashboard
    arms_above_shoulder: Optional[ArmsAboveShoulder] = None
    timeline: List[TimelinePoint]
    timeline_frames: List[TimelineFrame] = []
    critical_frames: List[CriticalFrame] = []
    action_items: List[ActionItem]


class AnalysisStatusResponse(BaseModel):
    status: str  # "processing" | "done" | "error"
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None
