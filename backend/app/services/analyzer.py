"""MediaPipe-based REBA analysis pipeline.

Runs as a FastAPI BackgroundTask. Steps:
  1. Download raw video from GCS  (uploads/{job_id}/video.mp4)
  2. Per-frame: anonymise head region (MediaPipe Pose bbox, top 38 % of
     person height + 20 px padding), write anonymised mp4 back to GCS
  3. REBA subscore calculation per sampled frame (every 25 frames ≈ 1 s)
  4. Aggregate timeline, movement classes, body-region scores, action items
  5. Write results/{job_id}/result.json to GCS
"""
import os
os.environ["DISPLAY"] = ""
os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"

import asyncio
import json
import logging
import tempfile
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions

from ..config import settings
from . import gcs

logger = logging.getLogger(__name__)

# ── MediaPipe Tasks model ─────────────────────────────────────────────────────
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
)
_MODEL_PATH = Path("/tmp/pose_landmarker_heavy.task")


def _ensure_model() -> None:
    """Download the pose landmarker model file if not already cached."""
    if not _MODEL_PATH.exists():
        logger.info("Downloading pose model → %s", _MODEL_PATH)
        urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
        logger.info("Pose model downloaded (%d bytes)", _MODEL_PATH.stat().st_size)


# ─────────────────────────────────────────────────────────────────────────────
# Geometry helpers
# ─────────────────────────────────────────────────────────────────────────────

def _angle_at_vertex(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle in degrees at vertex *b* formed by rays b→a and b→c."""
    ba = a - b
    bc = c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8
    return float(np.degrees(np.arccos(np.clip(np.dot(ba, bc) / denom, -1.0, 1.0))))


def _pt(landmarks, idx: int, w: int, h: int) -> np.ndarray:
    lm = landmarks[idx]
    return np.array([lm.x * w, lm.y * h])


# ─────────────────────────────────────────────────────────────────────────────
# REBA subscore calculation
# ─────────────────────────────────────────────────────────────────────────────

def _reba_subscores(landmarks, w: int, h: int) -> dict[str, float]:
    """Return per-region REBA-style subscores (raw, not yet normalised to 1-10)."""
    def pt(idx: int) -> np.ndarray:
        return _pt(landmarks, idx, w, h)

    l_shoulder, r_shoulder = pt(11), pt(12)
    l_elbow,    r_elbow    = pt(13), pt(14)
    l_wrist,    r_wrist    = pt(15), pt(16)
    l_hip,      r_hip      = pt(23), pt(24)
    l_knee,     r_knee     = pt(25), pt(26)
    l_ankle,    r_ankle    = pt(27), pt(28)
    nose                   = pt(0)

    mid_shoulder = (l_shoulder + r_shoulder) / 2
    mid_hip      = (l_hip      + r_hip)      / 2

    # ── Trunk (lumbar) ────────────────────────────────────────────────────────
    trunk_vec   = mid_hip - mid_shoulder
    trunk_angle = float(np.degrees(
        np.arctan2(abs(trunk_vec[0]), abs(trunk_vec[1]) + 1e-8)
    ))
    if   trunk_angle <  5:  lumbar = 1.0
    elif trunk_angle < 20:  lumbar = 2.5
    elif trunk_angle < 45:  lumbar = 5.5
    else:                   lumbar = 8.0

    # ── Neck ─────────────────────────────────────────────────────────────────
    neck_vec   = nose - mid_shoulder
    neck_angle = float(np.degrees(
        np.arctan2(abs(neck_vec[0]), abs(neck_vec[1]) + 1e-8)
    ))
    if   neck_angle < 10:  neck = 1.0
    elif neck_angle < 20:  neck = 3.0
    else:                  neck = 6.5

    # ── Shoulder / upper arm ─────────────────────────────────────────────────
    l_arm_angle = _angle_at_vertex(mid_shoulder, l_shoulder, l_elbow)
    r_arm_angle = _angle_at_vertex(mid_shoulder, r_shoulder, r_elbow)
    arm_angle   = max(l_arm_angle, r_arm_angle)
    if   arm_angle < 20:  shoulder = 1.5
    elif arm_angle < 45:  shoulder = 3.0
    elif arm_angle < 90:  shoulder = 5.5
    else:                 shoulder = 8.0

    # ── Forearm / lower arm ───────────────────────────────────────────────────
    l_elbow_angle = _angle_at_vertex(l_shoulder, l_elbow, l_wrist)
    r_elbow_angle = _angle_at_vertex(r_shoulder, r_elbow, r_wrist)
    elbow_angle   = max(l_elbow_angle, r_elbow_angle)
    forearm = 1.5 if 60 <= elbow_angle <= 100 else 4.5

    # ── Knee ─────────────────────────────────────────────────────────────────
    l_flex = 180 - _angle_at_vertex(l_hip, l_knee, l_ankle)
    r_flex = 180 - _angle_at_vertex(r_hip, r_knee, r_ankle)
    knee_flex = max(l_flex, r_flex)
    if   knee_flex < 30:  knee = 1.0
    elif knee_flex < 60:  knee = 3.5
    else:                 knee = 6.5

    return {
        "lumbar":     lumbar,
        "shoulder_l": shoulder * 0.90,
        "shoulder_r": shoulder,
        "neck":       neck,
        "knee_l":     knee * 0.95,
        "knee_r":     knee,
        "forearm":    forearm,
    }


# Max possible values per region (for normalisation to 1-10 later)
_REGION_MAX: dict[str, float] = {
    "lumbar":     8.0,
    "shoulder_l": 7.2,
    "shoulder_r": 8.0,
    "neck":       6.5,
    "knee_l":     6.175,
    "knee_r":     6.5,
    "forearm":    4.5,
}

_REGION_WEIGHTS: dict[str, float] = {
    "lumbar":     0.30,
    "neck":       0.20,
    "shoulder_l": 0.10,
    "shoulder_r": 0.10,
    "knee_l":     0.10,
    "knee_r":     0.10,
    "forearm":    0.10,
}


def _overall_reba(subscores: dict[str, float]) -> float:
    """Weighted combination → overall REBA score on 1-10 scale."""
    raw = sum(
        _REGION_WEIGHTS[k] * subscores[k] / _REGION_MAX[k]
        for k in _REGION_WEIGHTS
    )
    return round(1.0 + raw * 9.0, 2)


# ─────────────────────────────────────────────────────────────────────────────
# Movement classification (geometry-based, independent of REBA score)
# ─────────────────────────────────────────────────────────────────────────────

def _classify_movement(lm) -> str:
    """Classify movement using normalised landmark coordinates."""
    y_wrist_r   = lm[16].y
    y_wrist_l   = lm[15].y
    y_shoulder_r = lm[12].y
    y_shoulder_l = lm[11].y
    y_hip_r     = lm[24].y

    overhead = (y_wrist_r < y_shoulder_r - 0.05 or
                y_wrist_l < y_shoulder_l - 0.05)
    bending  = (y_shoulder_r < y_hip_r - 0.25 or
                y_shoulder_l < y_hip_r - 0.25)

    if overhead:
        return "overhead"
    elif bending:
        return "bending"
    else:
        return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# Frame-level anonymisation
# ─────────────────────────────────────────────────────────────────────────────

def _anonymise_frame(frame: np.ndarray, pose_result) -> np.ndarray:
    """Draw an opaque grey box over the head region (top 38 % + 20 px pad)."""
    if not pose_result.pose_landmarks:
        return frame

    h, w = frame.shape[:2]
    lm = pose_result.pose_landmarks[0]  # first detected person (Tasks API)

    vis_y = [lm[i].y * h for i in range(33) if (lm[i].visibility or 0) > 0.3]
    vis_x = [lm[i].x * w for i in range(33) if (lm[i].visibility or 0) > 0.3]
    if not vis_y:
        return frame

    p_top    = min(vis_y)
    p_bottom = max(vis_y)
    p_left   = min(vis_x)
    p_right  = max(vis_x)
    p_height = p_bottom - p_top

    PAD = 20
    box_top    = max(0, int(p_top)                         - PAD)
    box_bottom = min(h, int(p_top + 0.38 * p_height)      + PAD)
    box_left   = max(0, int(p_left)                        - PAD)
    box_right  = min(w, int(p_right)                       + PAD)

    cv2.rectangle(frame, (box_left, box_top), (box_right, box_bottom), (80, 80, 80), -1)
    return frame


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(job_id: str, meta: dict | None = None) -> None:
    """BackgroundTask: anonymise + REBA analysis; write result to GCS."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _pipeline_sync, job_id, meta or {})


def _pipeline_sync(job_id: str, meta: dict) -> None:
    logger.info("Pipeline start: %s", job_id)
    try:
        _run(job_id, meta)
    except Exception:
        logger.exception("Pipeline failed: %s", job_id)
        _write_error(job_id, "Analysis pipeline failed — see server logs.")


def _run(job_id: str, meta: dict) -> None:
    raw_path = f"{settings.UPLOAD_PREFIX}{job_id}/video.mp4"
    video_bytes = gcs.download_bytes(raw_path)

    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        anon_path  = Path(tmp) / "anon.mp4"
        input_path.write_bytes(video_bytes)

        cap     = cv2.VideoCapture(str(input_path))
        fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(anon_path), fourcc, fps, (frame_w, frame_h))

        _ensure_model()
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(_MODEL_PATH)),
            running_mode=vision.RunningMode.IMAGE,
        )
        landmarker = PoseLandmarker.create_from_options(options)

        sampled: list[dict] = []
        frame_idx = 0
        sample_interval = max(1, int(fps))  # ~1 sample per second

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = landmarker.detect(mp_image)
            frame    = _anonymise_frame(frame, result)
            writer.write(frame)

            if frame_idx % sample_interval == 0 and result.pose_landmarks:
                lm      = result.pose_landmarks[0]  # first detected person
                scores  = _reba_subscores(lm, frame_w, frame_h)
                overall = _overall_reba(scores)
                minute  = int(frame_idx / fps / 60)

                movement = _classify_movement(lm)

                frame_nr = len(sampled) + 1  # 1-indexed sample count
                if frame_nr <= 10:
                    print(
                        f"Frame {frame_nr}: y_schulter_r={lm[12].y:.3f}, "
                        f"y_hufte_r={lm[24].y:.3f}, "
                        f"diff={lm[24].y - lm[12].y:.3f}, "
                        f"y_handgelenk_r={lm[16].y:.3f}, "
                        f"movement={movement}"
                    )

                sampled.append({
                    "frame":         frame_idx,
                    "second":        round(frame_idx / fps, 1),
                    "minute":        minute,
                    "reba":          overall,
                    "region_scores": scores,
                    "movement":      movement,
                })

            frame_idx += 1

        cap.release()
        writer.release()
        landmarker.close()

        # Push anonymised video to GCS
        anon_bytes = anon_path.read_bytes()
        gcs.upload_bytes(
            f"{settings.UPLOAD_PREFIX}{job_id}/video_anon.mp4",
            anon_bytes,
            "video/mp4",
        )

        # Extract top-3 critical frames while anon_path is still on disk
        critical_frames = _extract_critical_frames(job_id, sampled, anon_path)

    result = _aggregate(job_id, sampled, fps, meta)
    result["critical_frames"] = critical_frames
    gcs.upload_bytes(
        f"{settings.RESULTS_PREFIX}{job_id}/result.json",
        json.dumps(result).encode(),
        "application/json",
    )
    logger.info("Pipeline done: %s  REBA=%.1f", job_id, result["reba_score"])


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate(job_id: str, sampled: list[dict], fps: float, meta: dict) -> dict:
    if not sampled:
        return _empty_result(job_id, meta)

    reba_vals = [f["reba"] for f in sampled]
    avg_reba  = float(np.mean(reba_vals))

    # Region averages
    region_avgs: dict[str, float] = {}
    for k in _REGION_MAX:
        vals = [f["region_scores"][k] for f in sampled if k in f.get("region_scores", {})]
        region_avgs[k] = float(np.mean(vals)) if vals else 1.0

    # Movement classification
    n = len(sampled)
    n_bend     = sum(1 for f in sampled if f["movement"] == "bending")
    n_overhead = sum(1 for f in sampled if f["movement"] == "overhead")
    n_neutral  = n - n_bend - n_overhead

    total_secs = len(sampled) * max(1, int(fps)) / fps
    shift_min  = int(meta.get("shift_duration_min") or max(1, int(total_secs / 60)))

    bend_pct  = round(n_bend     / n * 100, 1)
    over_pct  = round(n_overhead / n * 100, 1)
    neut_pct  = round(max(0.0, 100 - bend_pct - over_pct), 1)

    # Per-minute timeline
    by_minute: dict[int, list[float]] = {}
    for f in sampled:
        by_minute.setdefault(f["minute"], []).append(f["reba"])
    timeline = [
        {"minute": m, "reba": round(float(np.mean(vs)), 2)}
        for m, vs in sorted(by_minute.items())
    ]

    # REBA level
    if   avg_reba <= 4: level = "LOW"
    elif avg_reba <= 6: level = "MEDIUM"
    elif avg_reba <= 8: level = "HIGH"
    else:               level = "VERY_HIGH"

    return {
        "job_id":             job_id,
        "company_name":       meta.get("company_name"),
        "department":         meta.get("department"),
        "task_description":   meta.get("task_description"),
        "worker_height_cm":   meta.get("worker_height_cm"),
        "shift_duration_min": shift_min,
        "reba_score":         round(avg_reba, 2),
        "reba_level":         level,
        "body_regions":       region_avgs,
        "movements": {
            "bending":  {"pct": bend_pct, "minutes": round(shift_min * bend_pct / 100, 1)},
            "overhead": {"pct": over_pct, "minutes": round(shift_min * over_pct / 100, 1)},
            "neutral":  {"pct": neut_pct, "minutes": round(shift_min * neut_pct / 100, 1)},
        },
        "timeline":    timeline,
        "timeline_frames": [
            {"second": f["second"], "movement": f["movement"]}
            for f in sampled
        ],
        "action_items": _build_action_items(region_avgs, bend_pct, over_pct),
    }


def _build_action_items(regions: dict[str, float], bend_pct: float, over_pct: float) -> list[dict]:
    items: list[dict] = []

    lumbar = regions.get("lumbar", 0)
    if lumbar > 5 and bend_pct > 0:
        items.append({
            "priority":      "CRITICAL",
            "region":        "Lendenwirbel",
            "text":          f"Erhöhter Rumpfbeuge-Anteil ({bend_pct:.0f} % der Schichtzeit). "
                             "Arbeitshöhe auf Ellbogenniveau anpassen.",
            "reduction_pct": 40,
        })
    elif lumbar > 3:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Lendenwirbel",
            "text":          "Moderate Lendenbelastung. Regelmäßige Entlastungspausen empfohlen.",
            "reduction_pct": 20,
        })

    neck = regions.get("neck", 0)
    if neck > 4:
        items.append({
            "priority":      "CRITICAL",
            "region":        "Nacken",
            "text":          "Anhaltende Nackenbeugehaltung erkannt. Bildschirm- oder Materialhöhe prüfen.",
            "reduction_pct": 35,
        })
    elif neck > 2:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Nacken",
            "text":          "Nackenhaltung auffällig. Arbeitsoberfläche um 5–10 cm anheben.",
            "reduction_pct": 15,
        })

    shoulder = max(regions.get("shoulder_l", 0), regions.get("shoulder_r", 0))
    if over_pct > 0 and (over_pct > 15 or shoulder > 6):
        items.append({
            "priority":      "CRITICAL" if over_pct > 20 else "MEDIUM",
            "region":        "Schulter",
            "text":          f"Überkopfarbeit: {over_pct:.0f} % der Schichtzeit. "
                             "Arbeitsmittel in Greifhöhe bringen.",
            "reduction_pct": 50,
        })

    if regions.get("forearm", 0) > 3.5:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Unterarm",
            "text":          "Ungünstige Unterarmhaltung erkannt. Stützvorrichtungen prüfen.",
            "reduction_pct": 25,
        })

    items.sort(key=lambda x: 0 if x["priority"] == "CRITICAL" else 1)
    return items


def _empty_result(job_id: str, meta: dict | None = None) -> dict:
    m = meta or {}
    return {
        "job_id":             job_id,
        "company_name":       m.get("company_name"),
        "department":         m.get("department"),
        "task_description":   m.get("task_description"),
        "worker_height_cm":   m.get("worker_height_cm"),
        "shift_duration_min": int(m.get("shift_duration_min") or 0),
        "reba_score":         1.0,
        "reba_level":         "LOW",
        "body_regions":       {k: 1.0 for k in _REGION_MAX},
        "movements": {
            "bending":  {"pct": 0.0, "minutes": 0.0},
            "overhead": {"pct": 0.0, "minutes": 0.0},
            "neutral":  {"pct": 100.0, "minutes": 0.0},
        },
        "timeline":         [],
        "timeline_frames":  [],
        "critical_frames":  [],
        "action_items":     [],
    }


def _extract_critical_frames(
    job_id: str,
    sampled: list[dict],
    anon_path: Path,
) -> list[dict]:
    """Extract top-3 REBA frames from the anonymised video, overlay timestamp, upload to GCS."""
    if not sampled:
        return []

    top3 = sorted(sampled, key=lambda f: f["reba"], reverse=True)[:3]
    cap  = cv2.VideoCapture(str(anon_path))
    result: list[dict] = []

    for rank, fd in enumerate(top3, start=1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fd["frame"])
        ret, frame = cap.read()
        if not ret:
            continue

        sec   = fd["second"]
        label = f"{int(sec // 60):02d}:{int(sec % 60):02d} \u00b7 REBA {fd['reba']:.1f}"
        cv2.putText(
            frame, label, (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9,
            (255, 255, 255), 2, cv2.LINE_AA,
        )

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            continue

        filename = f"critical_{rank}.jpg"
        gcs_path = f"{settings.RESULTS_PREFIX}{job_id}/frames/{filename}"
        gcs.upload_bytes(gcs_path, buf.tobytes(), "image/jpeg")
        result.append({
            "rank":     rank,
            "second":   round(sec, 1),
            "reba":     fd["reba"],
            "movement": fd["movement"],
            "gcs_path": gcs_path,
        })

    cap.release()
    return result


def _write_error(job_id: str, msg: str) -> None:
    try:
        gcs.upload_bytes(
            f"{settings.RESULTS_PREFIX}{job_id}/result.json",
            json.dumps({"error": msg}).encode(),
            "application/json",
        )
    except Exception:
        logger.exception("Failed to write error result for %s", job_id)
