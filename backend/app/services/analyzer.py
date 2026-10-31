"""MediaPipe-based analysis pipeline: posture index based on REBA (1 to 10).

The value is a weighted index of body-region scores, not the standard REBA
(1 to 15 with load, coupling and activity); see docs/HALTUNGSINDEX.md.
Field names (reba_score, reba) stay for compatibility.

Runs as a FastAPI BackgroundTask. Steps:
  1. Download raw video from GCS  (raw/{job_id}/video.mp4) into a temp file
  2. Region scores, movement class and upper arm angle per sampled frame
     (every int(fps) frames, about one sample per second)
  3. Aggregate timeline, movement classes, body-region scores, action items;
     an error result instead when hardly any person was detected
  4. Three critical frames from the original video, heads and faces of all
     persons blacked out generously; frames without detection are dropped.
     No video is kept (decision on 31.10.2026).
  5. Write results/{job_id}/result.json to GCS
  6. Delete the raw video, also when the analysis failed
     (docs/LOESCHKONZEPT.md)

Optional: a PoseRecorder (services/workplace/pose_store.py) keeps the
per-frame landmarks for the Steckbrief module and writes
results/{job_id}/pose.npz. It does not change result.json.
"""
import os
os.environ["DISPLAY"] = ""
os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"

import asyncio
import hashlib
import json
import logging
import math
import tempfile
import threading
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, PoseLandmarker, PoseLandmarkerOptions

from ..config import settings
from . import gcs

logger = logging.getLogger(__name__)

# ── MediaPipe Tasks models ────────────────────────────────────────────────────
# Fixed versions with checksum; the Docker image contains both under
# MODEL_DIR (Dockerfile). Outside the image they are downloaded once.
_MODELS = {
    "pose": (
        "pose_landmarker_heavy.task",
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task",
        "64437af838a65d18e5ba7a0d39b465540069bc8aae8308de3e318aad31fcbc7b",
    ),
    "face": (
        "blaze_face_short_range.tflite",
        "https://storage.googleapis.com/mediapipe-models/face_detector/"
        "blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
        "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f",
    ),
}
_model_lock = threading.Lock()


def _model_path(name: str) -> Path:
    return Path(settings.MODEL_DIR) / _MODELS[name][0]


def _ensure_model(name: str = "pose") -> Path:
    """Model file, downloaded once if missing (never a half-written file)."""
    path = _model_path(name)
    with _model_lock:
        if not path.exists():
            _, url, sha = _MODELS[name]
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading model %s", path.name)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
                with urllib.request.urlopen(url, timeout=120) as resp:
                    tmp.write(resp.read())
            if hashlib.sha256(Path(tmp.name).read_bytes()).hexdigest() != sha:
                os.unlink(tmp.name)
                raise RuntimeError(f"Checksum of {path.name} does not match")
            os.replace(tmp.name, path)
    return path


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
    """Return per-region scores based on REBA (raw, not yet normalised to 1-10).

    Angles as in the REBA definition (corrected on 31.10.2026, same as the
    browser port motavi/src/analysis/reba.ts): neck = trunk axis against
    shoulder->ear midpoint, upper arm = angle to the trunk (shoulder->hip),
    lower arm = elbow flexion with 60 to 100 degrees as the neutral band.
    """
    def pt(idx: int) -> np.ndarray:
        return _pt(landmarks, idx, w, h)

    l_shoulder, r_shoulder = pt(11), pt(12)
    l_elbow,    r_elbow    = pt(13), pt(14)
    l_wrist,    r_wrist    = pt(15), pt(16)
    l_hip,      r_hip      = pt(23), pt(24)
    l_knee,     r_knee     = pt(25), pt(26)
    l_ankle,    r_ankle    = pt(27), pt(28)
    mid_ear                = (pt(7) + pt(8)) / 2

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

    # ── Neck: trunk axis extended above the shoulders vs. shoulder->ear midpoint
    trunk_up   = mid_shoulder + (mid_shoulder - mid_hip)
    neck_angle = _angle_at_vertex(trunk_up, mid_shoulder, mid_ear)
    if   neck_angle < 10:  neck = 1.0
    elif neck_angle < 20:  neck = 3.0
    else:                  neck = 6.5

    # ── Upper arm: angle between upper arm and trunk (shoulder->hip) ─────────
    l_arm_angle = _angle_at_vertex(l_hip, l_shoulder, l_elbow)
    r_arm_angle = _angle_at_vertex(r_hip, r_shoulder, r_elbow)
    arm_angle   = max(l_arm_angle, r_arm_angle)
    if   arm_angle < 20:  shoulder = 1.5
    elif arm_angle < 45:  shoulder = 3.0
    elif arm_angle < 90:  shoulder = 5.5
    else:                 shoulder = 8.0

    # ── Lower arm: elbow flexion, 60 to 100 degrees is the neutral REBA band ──
    l_elbow_angle = _angle_at_vertex(l_shoulder, l_elbow, l_wrist)
    r_elbow_angle = _angle_at_vertex(r_shoulder, r_elbow, r_wrist)
    flexion = 180 - max(l_elbow_angle, r_elbow_angle)
    forearm = 1.5 if 60 <= flexion <= 100 else 4.5

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


def stufe(index: float) -> str:
    """Level of the posture index (1 to 10), same bands everywhere
    (docs/HALTUNGSINDEX.md): below 4 low, 4 to below 6 medium, 6 to below 8
    high, from 8 very high."""
    if index < 4:
        return "LOW"
    if index < 6:
        return "MEDIUM"
    if index < 8:
        return "HIGH"
    return "VERY_HIGH"


# ─────────────────────────────────────────────────────────────────────────────
# Movement classification (geometry-based, independent of REBA score)
# ─────────────────────────────────────────────────────────────────────────────

def _trunk_angle(lm, w: int, h: int) -> float:
    """Trunk inclination in degrees (0 = upright, 90 = horizontal).

    Computed in pixels like the REBA part: normalised x and y have different
    scales unless the video is square.
    """
    sx = (lm[11].x + lm[12].x) / 2 * w
    sy = (lm[11].y + lm[12].y) / 2 * h
    hx = (lm[23].x + lm[24].x) / 2 * w
    hy = (lm[23].y + lm[24].y) / 2 * h
    dx = sx - hx
    dy = sy - hy
    return math.degrees(math.atan2(abs(dx), abs(dy)))


def _ear_height(lm) -> float:
    """Normalised y of the ears (mean of the visible ones); nose as fallback."""
    ears = [lm[i].y for i in (7, 8) if (lm[i].visibility or 0) > 0.3]
    return sum(ears) / len(ears) if ears else lm[0].y


def _upper_arm_elevation(lm, w: int, h: int) -> float:
    """Larger of both upper arm angles to the trunk in degrees, in pixels.

    0 = arm hanging along the trunk, 90 = arm at shoulder height,
    180 = arm straight up. 2D: an arm pointing at the camera appears lower.
    """
    def p(i: int) -> np.ndarray:
        return np.array([lm[i].x * w, lm[i].y * h])

    trunk_down = (p(23) + p(24)) / 2 - (p(11) + p(12)) / 2
    angles = []
    for shoulder, elbow in ((11, 13), (12, 14)):
        arm = p(elbow) - p(shoulder)
        denom = np.linalg.norm(arm) * np.linalg.norm(trunk_down) + 1e-8
        angles.append(float(np.degrees(np.arccos(np.clip(np.dot(arm, trunk_down) / denom, -1.0, 1.0)))))
    return max(angles)


def _classify_movement(lm, w: int, h: int) -> str:
    """Classify movement from landmark coordinates.

    Overhead: a wrist above ear height (smaller y = higher in the image).
    Bending: trunk inclination above settings.MOVEMENT_BENDING_DEG.
    Overhead takes priority over bending.
    """
    ear_y = _ear_height(lm)
    ueberkopf = min(lm[15].y, lm[16].y) < ear_y - settings.MOVEMENT_OVERHEAD_MARGIN
    buecken = _trunk_angle(lm, w, h) > settings.MOVEMENT_BENDING_DEG

    if ueberkopf:
        return "overhead"
    elif buecken:
        return "bending"
    else:
        return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# Anonymisation of the critical frames (E.3.2 of the review on 31.10.2026)
# ─────────────────────────────────────────────────────────────────────────────

# Up to this many persons per critical frame get their head blacked out
_MAX_PERSONEN = 6
# Face boxes of the face detector are enlarged by this factor
_GESICHT_RAND = 1.6


def _kopfbox(lm, w: int, h: int) -> tuple[int, int, int, int]:
    """Generous box around the head of one person, in pixels.

    Uses all head landmarks (0 to 10, estimated also when hidden). The size
    is the largest of: 0.75 x shoulder width, 1.5 x head span, 0.45 x trunk
    length, 4 % of the frame; so it stays large in side view too.
    """
    p = np.array([[lm[i].x * w, lm[i].y * h] for i in range(33)])
    kopf = p[0:11]
    cx, cy = kopf.mean(axis=0)
    schultern = np.linalg.norm(p[11] - p[12])
    spanne = float(np.ptp(kopf, axis=0).max())
    rumpf = np.linalg.norm((p[11] + p[12]) / 2 - (p[23] + p[24]) / 2)
    r = max(0.75 * schultern, 1.5 * spanne, 0.45 * rumpf, 0.04 * max(w, h))
    return (max(0, int(cx - r)), max(0, int(cy - 1.2 * r)), min(w, int(cx + r)), min(h, int(cy + r)))


def _gesichtsbox(det, w: int, h: int) -> tuple[int, int, int, int]:
    bb = det.bounding_box
    cx, cy = bb.origin_x + bb.width / 2, bb.origin_y + bb.height / 2
    hw, hh = bb.width * _GESICHT_RAND / 2, bb.height * _GESICHT_RAND / 2
    return (max(0, int(cx - hw)), max(0, int(cy - hh)), min(w, int(cx + hw)), min(h, int(cy + hh)))


def _schwaerzen(frame: np.ndarray, personen, gesichter) -> np.ndarray | None:
    """Black out the heads of all detected persons and all detected faces.

    Returns None when no person is detected: such a frame is not kept, because
    nothing guarantees that a face in it is covered (fail closed).
    """
    if not personen:
        return None
    h, w = frame.shape[:2]
    boxen = [_kopfbox(lm, w, h) for lm in personen] + [_gesichtsbox(d, w, h) for d in gesichter]
    for x0, y0, x1, y1 in boxen:
        cv2.rectangle(frame, (x0, y0), (x1, y1), (0, 0, 0), -1)
    return frame


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(job_id: str, meta: dict | None = None, recorder=None) -> None:
    """BackgroundTask: analysis; write result to GCS."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _pipeline_sync, job_id, meta or {}, recorder)


def _pipeline_sync(job_id: str, meta: dict, recorder=None) -> None:
    logger.info("Pipeline start: %s", job_id)
    try:
        _run(job_id, meta, recorder)
    except Exception:
        logger.exception("Pipeline failed: %s", job_id)
        _write_error(job_id, "Die Analyse ist fehlgeschlagen. Bitte versuchen Sie es erneut oder wenden Sie sich an uns.")
    finally:
        _delete_raw(job_id)


def _delete_raw(job_id: str) -> None:
    """Delete the raw video right after the analysis. If this fails, the
    bucket lifecycle rule for raw/ deletes it after one day."""
    path = gcs.raw_video_path(job_id)
    try:
        gcs.delete_blob(path)
        logger.info("Raw video deleted: %s", job_id)
    except Exception:
        logger.exception("Deleting the raw video failed: %s", job_id)


def _run(job_id: str, meta: dict, recorder=None) -> None:
    raw_path = gcs.raw_video_path(job_id)

    with tempfile.TemporaryDirectory() as tmp:
        input_path = Path(tmp) / "input.mp4"
        gcs.download_to_file(raw_path, str(input_path))

        cap     = cv2.VideoCapture(str(input_path))
        fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if recorder is not None:
            recorder.start(fps, frame_w, frame_h)

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(_ensure_model("pose"))),
            running_mode=vision.RunningMode.IMAGE,
        )
        landmarker = PoseLandmarker.create_from_options(options)

        sampled: list[dict] = []
        frame_idx = 0
        proben = 0  # sample points, with or without a detected person
        sample_interval = max(1, int(fps))  # ~1 sample per second

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = landmarker.detect(mp_image)
            if recorder is not None:
                recorder.add(frame_idx, result)

            if frame_idx % sample_interval == 0:
                proben += 1
            if frame_idx % sample_interval == 0 and result.pose_landmarks:
                lm      = result.pose_landmarks[0]  # first detected person
                scores  = _reba_subscores(lm, frame_w, frame_h)
                overall = _overall_reba(scores)
                minute  = int(frame_idx / fps / 60)

                movement = _classify_movement(lm, frame_w, frame_h)
                arm_deg  = _upper_arm_elevation(lm, frame_w, frame_h)

                sampled.append({
                    "frame":         frame_idx,
                    "second":        round(frame_idx / fps, 1),
                    "minute":        minute,
                    "reba":          overall,
                    "region_scores": scores,
                    "movement":      movement,
                    "arm_deg":       arm_deg,
                })

            frame_idx += 1

        cap.release()
        landmarker.close()

        erkennung = len(sampled) / proben if proben else 0.0
        fehler = _erkennung_fehler(erkennung)
        if fehler:
            _write_error(job_id, fehler)
            return

        # Critical frames from the original video while it is still on disk
        critical_frames = _extract_critical_frames(job_id, sampled, input_path)

    # frame_idx counts every decoded frame, with or without a detected person
    duration_s = frame_idx / fps
    if recorder is not None:
        _save_pose(job_id, recorder)

    result = _aggregate(job_id, sampled, duration_s, meta)
    result["erkennung_anteil"] = round(erkennung, 3)
    result["critical_frames"] = critical_frames
    gcs.upload_bytes(
        f"{settings.RESULTS_PREFIX}{job_id}/result.json",
        json.dumps(result).encode(),
        "application/json",
    )
    logger.info("Pipeline done: %s  index=%.1f", job_id, result["reba_score"])


def _erkennung_fehler(anteil: float) -> str | None:
    """Message for the dashboard when too few frames show a person (E.3.5)."""
    if anteil == 0:
        return ("Im Video wurde keine Person erkannt. Bitte prüfen Sie die Aufnahme: "
                "ganze Person im Bild, fest stehende Kamera, gutes Licht.")
    if anteil < settings.ANALYSE_MIN_ERKENNUNG:
        return (f"Die Person wurde nur in {anteil * 100:.0f} % der Aufnahme erkannt. "
                "Für eine belastbare Auswertung bitte neu aufnehmen: ganze Person im Bild, "
                "fest stehende Kamera, gutes Licht.")
    return None


def _save_pose(job_id: str, recorder) -> None:
    """Write pose.npz before result.json; a failure here never stops the analysis."""
    try:
        gcs.upload_bytes(
            f"{settings.RESULTS_PREFIX}{job_id}/pose.npz",
            recorder.to_npz_bytes(),
            "application/octet-stream",
        )
    except Exception:
        logger.exception("Saving pose data failed: %s", job_id)


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate(job_id: str, sampled: list[dict], duration_s: float, meta: dict) -> dict:
    """sampled: at least one frame with a detected person (_erkennung_fehler)."""
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

    # Actual video duration, not only the samples with a detected person
    shift_min  = int(meta.get("shift_duration_min") or max(1, int(duration_s / 60)))

    bend_pct  = round(n_bend     / n * 100, 1)
    over_pct  = round(n_overhead / n * 100, 1)
    neut_pct  = round(max(0.0, 100 - bend_pct - over_pct), 1)

    # Arms above shoulder height: own metric, independent of the movement
    # classes (not yet shown as a class in the dashboard)
    arm_limit = settings.ARM_ELEVATION_DEG
    arm_pct   = round(sum(1 for f in sampled if f["arm_deg"] >= arm_limit) / n * 100, 1)

    # Per-minute timeline
    by_minute: dict[int, list[float]] = {}
    for f in sampled:
        by_minute.setdefault(f["minute"], []).append(f["reba"])
    timeline = [
        {"minute": m, "reba": round(float(np.mean(vs)), 2)}
        for m, vs in sorted(by_minute.items())
    ]

    level = stufe(avg_reba)

    return {
        "job_id":             job_id,
        "company_name":       meta.get("company_name"),
        "department":         meta.get("department"),
        "task_description":   meta.get("task_description"),
        "shift_duration_min": shift_min,
        "reba_score":         round(avg_reba, 2),
        "reba_max":           round(max(reba_vals), 2),
        "reba_level":         level,
        "body_regions":       region_avgs,
        "movements": {
            "bending":  {"pct": bend_pct, "minutes": round(shift_min * bend_pct / 100, 1)},
            "overhead": {"pct": over_pct, "minutes": round(shift_min * over_pct / 100, 1)},
            "neutral":  {"pct": neut_pct, "minutes": round(shift_min * neut_pct / 100, 1)},
        },
        "arms_above_shoulder": {
            "threshold_deg": arm_limit,
            "pct":           arm_pct,
            "minutes":       round(shift_min * arm_pct / 100, 1),
            "max_deg":       round(max(f["arm_deg"] for f in sampled), 1),
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
                             "Arbeitshöhe auf Ellbogenniveau anpassen."
        })
    elif lumbar > 3:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Lendenwirbel",
            "text":          "Moderate Lendenbelastung. Regelmäßige Entlastungspausen empfohlen."
        })

    neck = regions.get("neck", 0)
    if neck > 4:
        items.append({
            "priority":      "CRITICAL",
            "region":        "Nacken",
            "text":          "Anhaltende Nackenbeugehaltung erkannt. Bildschirm- oder Materialhöhe prüfen."
        })
    elif neck > 2:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Nacken",
            "text":          "Nackenhaltung auffällig. Arbeitsoberfläche anheben, bis der Blick ohne Beugen des Nackens auf das Werkstück fällt."
        })

    shoulder = max(regions.get("shoulder_l", 0), regions.get("shoulder_r", 0))
    if over_pct > 0 and (over_pct > 15 or shoulder > 6):
        items.append({
            "priority":      "CRITICAL" if over_pct > 20 else "MEDIUM",
            "region":        "Schulter",
            "text":          f"Überkopfarbeit: {over_pct:.0f} % der Schichtzeit. "
                             "Arbeitsmittel in Greifhöhe bringen."
        })

    if regions.get("forearm", 0) > 3.5:
        items.append({
            "priority":      "MEDIUM",
            "region":        "Unterarm",
            "text":          "Ungünstige Unterarmhaltung erkannt. Stützvorrichtungen prüfen."
        })

    items.sort(key=lambda x: 0 if x["priority"] == "CRITICAL" else 1)
    return items


def _extract_critical_frames(
    job_id: str,
    sampled: list[dict],
    video_path: Path,
) -> list[dict]:
    """Top-3 frames by posture index from the original video, heads and faces
    of all persons blacked out (_schwaerzen); frames without detection are
    dropped. Timestamp and value overlaid, uploaded to GCS."""
    if not sampled:
        return []

    top3 = sorted(sampled, key=lambda f: f["reba"], reverse=True)[:3]
    try:
        personen_lm = PoseLandmarker.create_from_options(PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(_ensure_model("pose"))),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=_MAX_PERSONEN,
            min_pose_detection_confidence=0.3,
        ))
        gesichter_det = FaceDetector.create_from_options(FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(_ensure_model("face"))),
            running_mode=vision.RunningMode.IMAGE,
            min_detection_confidence=0.3,
        ))
    except Exception:
        # without detectors no frame is anonymised safely, so none is kept
        logger.exception("Detectors for the critical frames unavailable: %s", job_id)
        return []

    cap = cv2.VideoCapture(str(video_path))
    result: list[dict] = []
    try:
        for fd in top3:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fd["frame"])
            ret, frame = cap.read()
            if not ret:
                continue
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            personen = personen_lm.detect(mp_image).pose_landmarks
            gesichter = gesichter_det.detect(mp_image).detections
            frame = _schwaerzen(frame, personen, gesichter)
            if frame is None:
                continue

            sec   = fd["second"]
            # Hershey fonts know ASCII only
            label = f"{int(sec // 60):02d}:{int(sec % 60):02d}   Haltungsindex {fd['reba']:.1f}".replace(".", ",")
            cv2.putText(
                frame, label, (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (255, 255, 255), 2, cv2.LINE_AA,
            )

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                continue

            rank     = len(result) + 1
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
    finally:
        cap.release()
        personen_lm.close()
        gesichter_det.close()
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
