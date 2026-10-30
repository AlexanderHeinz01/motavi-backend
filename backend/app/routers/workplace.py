"""Steckbrief module: process steps and expert review (STECKBRIEF_MODUL §4.3, §6).

Only for signed-in consultants (role "berater" or "admin").

GET  /workplace/{job_id}/ablauf  proposal in the median cycle, saved review, result
PUT  /workplace/{job_id}/review  confirm or correct the steps; transferred to all cycles
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..config import settings
from ..schemas.workplace import (
    AblaufErgebnisDaten,
    AblaufResponse,
    MedianZyklusDaten,
    ReviewGespeichert,
    ReviewRequest,
    SegmentVorschlag,
    ZyklenInfo,
)
from ..services import gcs
from ..services.workplace.cycles import detect_cycles
from ..services.workplace.pose_store import load_npz
from ..services.workplace.preprocess import prepare
from ..services.workplace.segments import (
    STEP_TYPES,
    BewerteterSchritt,
    median_cycle,
    propose_segments,
    transfer,
    validate_review,
)
from .auth import require_berater

router = APIRouter()


def _path(job_id: str, name: str) -> str:
    return f"{settings.RESULTS_PREFIX}{job_id}/{name}"


def _analyse(job_id: str):
    """Pose data of the job -> prepared data, cycles, median cycle, proposal."""
    try:
        data = gcs.download_bytes(_path(job_id, "pose.npz"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Für diesen Job liegen keine Pose-Daten vor.")
    result = gcs.get_result(job_id) or {}
    shift_min = float(result.get("shift_duration_min") or 480)
    prep = prepare(load_npz(data))
    zyklen = detect_cycles(prep, shift_min)
    median = median_cycle(prep, zyklen)
    vorschlag = propose_segments(median) if median else []
    return zyklen, median, vorschlag


def _response(job_id: str, zyklen, median, vorschlag, review: dict | None) -> AblaufResponse:
    ergebnis = None
    if review and zyklen.erkannt:
        schritte = [BewerteterSchritt(s["start_phase"], s["ende_phase"], s["typ"], s["klasse"]) for s in review["segmente"]]
        e = transfer(schritte, zyklen)
        ergebnis = AblaufErgebnisDaten(
            ablaufschritte=e.ablaufschritte, anteile_ablauf=e.anteile_ablauf, sekunden_je_zyklus=e.sekunden_je_zyklus,
            minuten_pro_schicht=e.minuten_pro_schicht, anzahl_zyklen=e.anzahl_zyklen, hinweis=e.hinweis,
        )
    return AblaufResponse(
        job_id=job_id,
        zyklen=ZyklenInfo(
            erkannt=zyklen.erkannt, hinweis=zyklen.hinweis, median_s=zyklen.zykluszeit_median.wert,
            anzahl_gueltig=zyklen.anzahl_gueltig, konfidenz=round(zyklen.konfidenz, 3),
            zyklen_pro_schicht=zyklen.zyklen_pro_schicht.wert,
        ),
        median_zyklus=MedianZyklusDaten(
            dauer_s=median.dauer_s, anzahl_zyklen=median.anzahl_zyklen,
            phase=[round(float(p), 4) for p in median.phase],
            hand_speed=[round(float(v), 3) for v in median.hand_speed],
            hip_speed=[round(float(v), 3) for v in median.hip_speed],
        ) if median else None,
        vorschlag=[
            SegmentVorschlag(
                start_phase=s.start_phase, ende_phase=s.ende_phase,
                start_s=round(s.start_phase * median.dauer_s, 2), ende_s=round(s.ende_phase * median.dauer_s, 2),
                dauer_s=round(s.dauer(median.dauer_s), 2), art=s.art, vorschlag_typ=s.vorschlag_typ,
            )
            for s in vorschlag
        ],
        typen=STEP_TYPES,
        review=ReviewGespeichert(**review) if review else None,
        ergebnis=ergebnis,
    )


@router.get("/workplace/{job_id}/ablauf", response_model=AblaufResponse)
async def get_ablauf(job_id: str, user: dict = Depends(require_berater)) -> AblaufResponse:
    zyklen, median, vorschlag = _analyse(job_id)
    review = gcs.get_json(_path(job_id, "review.json"))
    return _response(job_id, zyklen, median, vorschlag, review)


@router.put("/workplace/{job_id}/review", response_model=AblaufResponse)
async def put_review(job_id: str, body: ReviewRequest, user: dict = Depends(require_berater)) -> AblaufResponse:
    zyklen, median, vorschlag = _analyse(job_id)
    if not zyklen.erkannt:
        raise HTTPException(status_code=409, detail=f"{zyklen.hinweis}: Ablaufschritte lassen sich nicht auf Zyklen übertragen.")
    segmente = sorted(body.segmente, key=lambda s: s.start_phase)
    schritte = [
        BewerteterSchritt(s.start_phase, s.ende_phase, s.typ, s.klasse or STEP_TYPES.get(s.typ, ""))
        for s in segmente
    ]
    errors = validate_review(schritte)
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    review = {
        "segmente": [
            {"start_phase": s.start_phase, "ende_phase": s.ende_phase, "typ": s.typ, "klasse": s.klasse}
            for s in schritte
        ],
        "kommentar": body.kommentar,
        "bestaetigt_von": user["email"],
        "bestaetigt_am": datetime.now(timezone.utc).isoformat(),
    }
    gcs.put_json(_path(job_id, "review.json"), review)
    return _response(job_id, zyklen, median, vorschlag, review)
