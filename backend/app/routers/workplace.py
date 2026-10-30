"""Steckbrief module API (STECKBRIEF_MODUL §4.3 to §6).

GET  /workplace/{job_id}            Steckbrief: scores, recommendation, type, economics (signed in)
PUT  /workplace/{job_id}/inputs     customer inputs (signed in)
GET  /workplace/{job_id}/pdf        PDF Steckbrief, 2 pages (signed in)
GET  /workplace/{job_id}/export     JSON export, docs/steckbrief_schema.json (signed in)
GET  /workplace/{job_id}/ablauf     proposal in the median cycle, saved review, result (consultants)
PUT  /workplace/{job_id}/review     confirm or correct the steps; transferred to all cycles (consultants)
PUT  /workplace/{job_id}/empfehlung confirm or change recommendation and type (consultants)

Consultants: role "berater" or "admin".
"""
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse

from ..config import settings
from ..schemas.workplace import (
    AblaufErgebnisDaten,
    AblaufResponse,
    EmpfehlungBestaetigung,
    Kundenangaben,
    MedianZyklusDaten,
    ReviewGespeichert,
    ReviewRequest,
    SegmentVorschlag,
    ZyklenInfo,
)
from ..services import gcs
from ..services.workplace import export, pdf_steckbrief, scoring_config, steckbrief
from ..services.workplace.belastung import analyse_belastung
from ..services.workplace.cycles import detect_cycles
from ..services.workplace.pose_store import load_npz
from ..services.workplace.preprocess import prepare
from ..services.workplace.reach import analyse_reach
from ..services.workplace.segments import (
    STEP_TYPES,
    BewerteterSchritt,
    median_cycle,
    propose_segments,
    transfer,
    validate_review,
)
from .auth import get_current_user, require_berater

router = APIRouter()


def _path(job_id: str, name: str) -> str:
    return f"{settings.RESULTS_PREFIX}{job_id}/{name}"


def _load(job_id: str, kunde: dict | None = None):
    """Pose data, result.json and customer inputs of the job -> prepared data and cycles.

    kunde: customer inputs to use instead of the saved ones. The cycles per
    shift use the customer's shift duration if given, otherwise the one of
    the ergonomics analysis.
    """
    try:
        data = gcs.download_bytes(_path(job_id, "pose.npz"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Für diesen Job liegen keine Pose-Daten vor.")
    result = gcs.get_result(job_id) or {}
    if kunde is None:
        kunde = gcs.get_json(_path(job_id, "inputs.json")) or {}
    shift_min = float(kunde.get("schichtdauer_min") or result.get("shift_duration_min") or 480)
    prep = prepare(load_npz(data))
    zyklen = detect_cycles(prep, shift_min)
    return prep, zyklen, result, kunde


def _analyse(job_id: str):
    """Cycles, median cycle and segment proposal of the job."""
    prep, zyklen, _, _ = _load(job_id)
    median = median_cycle(prep, zyklen)
    vorschlag = propose_segments(median) if median else []
    return zyklen, median, vorschlag


def _schritte(review: dict | None) -> list[BewerteterSchritt] | None:
    if not review:
        return None
    return [BewerteterSchritt(s["start_phase"], s["ende_phase"], s["typ"], s["klasse"]) for s in review["segmente"]]


def _response(job_id: str, zyklen, median, vorschlag, review: dict | None) -> AblaufResponse:
    ergebnis = None
    if review and zyklen.erkannt:
        e = transfer(_schritte(review), zyklen)
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


def _arbeitsplatz(result: dict) -> str | None:
    """Name of the workplace from the upload form (no person)."""
    teile = [result.get(k) for k in ("department", "task_description") if result.get(k)]
    return " · ".join(teile) or None


def _ergebnisse(job_id: str, kunde: dict | None = None) -> dict:
    """Module results of the job: keyword arguments for steckbrief.build."""
    prep, zyklen, result, kunde = _load(job_id, kunde)
    review = gcs.get_json(_path(job_id, "review.json"))
    schritte = _schritte(review) if zyklen.erkannt else None
    return dict(
        zyklen=zyklen, greifraum=analyse_reach(prep), schritte=schritte,
        ablauf=transfer(schritte, zyklen) if schritte else None,
        belastung=analyse_belastung(result, prep, zyklen), kunde=kunde, review=review,
        arbeitsplatz=_arbeitsplatz(result),
    )


def _steckbrief(job_id: str, kunde: dict | None = None, bestaetigung: dict | None = None, speichern: bool = True) -> dict:
    """bestaetigung: use this instead of the saved one (None: saved one)."""
    if bestaetigung is None:
        bestaetigung = gcs.get_json(_path(job_id, "empfehlung.json"))
    doc = steckbrief.build(scoring_config.get(), job_id, **_ergebnisse(job_id, kunde), bestaetigung=bestaetigung or None)
    if speichern:
        gcs.put_json(_path(job_id, "workplace.json"), doc)
    return doc


@router.get("/workplace/{job_id}")
async def get_steckbrief(job_id: str, user: dict = Depends(get_current_user)) -> dict:
    """Steckbrief with scores, recommendation (proposal), type and economics."""
    return _steckbrief(job_id)


@router.put("/workplace/{job_id}/inputs")
async def put_inputs(job_id: str, body: Kundenangaben, user: dict = Depends(get_current_user)) -> dict:
    """Save the customer inputs and return the recomputed Steckbrief."""
    kunde = body.model_dump(exclude_none=True)
    doc = _steckbrief(job_id, kunde)  # 404 without pose data, before anything is saved
    gcs.put_json(_path(job_id, "inputs.json"), kunde)
    return doc


@router.put("/workplace/{job_id}/empfehlung")
async def put_empfehlung(job_id: str, body: EmpfehlungBestaetigung, user: dict = Depends(require_berater)) -> dict:
    """The expert confirms or changes recommendation and automation type (§5.3, §5.4, §6.4)."""
    cfg = scoring_config.get()
    mit_auto = body.empfehlung_id in cfg.empfehlung.mit_automatisierung
    if body.typ_id is not None:
        if not mit_auto:
            raise HTTPException(status_code=422, detail="Ein Automatisierungstyp gehört nur zu einer Empfehlung mit Automatisierung.")
        if steckbrief.typ_regel(cfg, body.typ_id) is None:
            raise HTTPException(status_code=422, detail=f"Unbekannter Automatisierungstyp {body.typ_id!r}.")
    # the current proposal, so that a later change of it can be pointed out
    vorschlag = _steckbrief(job_id, bestaetigung={}, speichern=False)
    bestaetigung = {
        "empfehlung_id": body.empfehlung_id,
        "typ_id": body.typ_id,
        "kommentar": body.kommentar,
        "vorschlag_id": vorschlag["empfehlung"]["vorschlag_id"],
        "vorschlag_typ_id": vorschlag["automatisierungstyp"]["vorschlag_id"],
        "bestaetigt_von": user["email"],
        "bestaetigt_am": datetime.now(timezone.utc).isoformat(),
    }
    gcs.put_json(_path(job_id, "empfehlung.json"), bestaetigung)
    return _steckbrief(job_id, bestaetigung=bestaetigung)


def _dateiname(doc: dict, endung: str) -> str:
    return f"motavi-steckbrief-{doc['job_id'][:8]}.{endung}"


@router.get("/workplace/{job_id}/pdf")
async def get_pdf(job_id: str, user: dict = Depends(get_current_user)) -> StreamingResponse:
    doc = _steckbrief(job_id)
    e = scoring_config.get().empfehlung
    data = pdf_steckbrief.generate(doc, (e.schwelle_verbesserung, e.schwelle_automatisierung))
    return StreamingResponse(
        io.BytesIO(data), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_dateiname(doc, "pdf")}"'},
    )


@router.get("/workplace/{job_id}/export")
async def get_export(job_id: str, user: dict = Depends(get_current_user)) -> Response:
    doc = _steckbrief(job_id)
    body = json.dumps(export.to_export(doc), ensure_ascii=False, indent=2)
    return Response(
        body, media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{_dateiname(doc, "json")}"'},
    )
