"""Validation of the Steckbrief metrics against manual time stamps (S6,
STECKBRIEF_MODUL §8).

    python -m backend.scripts.validate_steckbrief manuell.csv --daten DIR --out docs/validierung_steckbrief.md

manuell.csv (UTF-8, comma separated, lines starting with # are comments):

    video,start_s,ende_s,typ
    montage_a.mp4,12.4,50.9,Zyklus          one row per manually measured cycle
    montage_a.mp4,12.4,18.0,Gehen           process steps (types of the expert view), optional
    nacharbeit.mp4,0,300,kein Zyklus        the person sees no recurring cycle in this video

Per video in DIR (first match wins):
    DIR/<video>/pose.npz, optional DIR/<video>/review.json
    DIR/<stem>.npz,       optional DIR/<stem>.review.json
    DIR/<video> as a video file: the pose is detected like in the pipeline
                          (MediaPipe, local, nothing is uploaded) and kept as DIR/<stem>.npz
pose.npz and review.json of a job are in the bucket under results/{job_id}/.

Metrics per video (§8.2): deviation of the median cycle time, of the number
of cycles, share of falsely detected cycles (a detected cycle is correct if it
overlaps a manual cycle with an IoU of at least 0.5, one to one), share of
missed cycles, deviation of the time share of waste (needs process steps in
the CSV and review.json). Target of the pilot phase: median cycle time within
±10 % of the manual measurement (§8.3). The other targets were confirmed on
30.10.2026 (STECKBRIEF_MODUL §8).
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import numpy as np

from backend.app.services.workplace.cycles import ZyklusErgebnis, detect_cycles
from backend.app.services.workplace.pose_store import load_npz
from backend.app.services.workplace.preprocess import prepare
from backend.app.services.workplace.segments import STEP_TYPES, AblaufErgebnis, BewerteterSchritt, transfer

ZYKLUS = "zyklus"
KEIN_ZYKLUS = "kein zyklus"
VIDEO_ENDUNGEN = (".mp4", ".mov", ".avi", ".mkv", ".m4v")


# ── manual time stamps ───────────────────────────────────────────────────────


@dataclass
class Manuell:
    zyklen: list[tuple[float, float]] = field(default_factory=list)
    segmente: list[tuple[float, float, str]] = field(default_factory=list)
    kein_zyklus: bool = False


class CsvFehler(ValueError):
    pass


def lese_csv(path: Path) -> dict[str, Manuell]:
    """Manual time stamps per video; errors name the line."""
    out: dict[str, Manuell] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        zeilen = [(i, z) for i, z in enumerate(csv.reader(f), start=1) if z and not z[0].lstrip().startswith("#")]
    if not zeilen or [c.strip().lower() for c in zeilen[0][1]] != ["video", "start_s", "ende_s", "typ"]:
        raise CsvFehler("Erste Zeile muss lauten: video,start_s,ende_s,typ")
    typen = {t.lower(): t for t in STEP_TYPES}
    for nr, z in zeilen[1:]:
        if len(z) != 4:
            raise CsvFehler(f"Zeile {nr}: vier Spalten erwartet, {len(z)} gefunden")
        video, a, b, typ = (c.strip() for c in z)
        try:
            start, ende = float(a.replace(",", ".")), float(b.replace(",", "."))
        except ValueError:
            raise CsvFehler(f"Zeile {nr}: start_s und ende_s müssen Zahlen sein") from None
        if not video:
            raise CsvFehler(f"Zeile {nr}: Video fehlt")
        if ende <= start or start < 0:
            raise CsvFehler(f"Zeile {nr}: ende_s muss nach start_s liegen, start_s ab 0")
        m = out.setdefault(video, Manuell())
        t = typ.lower()
        if t == ZYKLUS:
            m.zyklen.append((start, ende))
        elif t == KEIN_ZYKLUS:
            m.kein_zyklus = True
        elif t in typen:
            m.segmente.append((start, ende, typen[t]))
        else:
            raise CsvFehler(f"Zeile {nr}: unbekannter Typ {typ!r} (Zyklus, kein Zyklus oder {', '.join(STEP_TYPES)})")
    for video, m in out.items():
        if m.kein_zyklus and m.zyklen:
            raise CsvFehler(f"{video}: \"kein Zyklus\" und Zyklen zugleich")
        if not m.kein_zyklus and not m.zyklen:
            raise CsvFehler(f"{video}: keine Zyklen erfasst (oder eine Zeile \"kein Zyklus\")")
        m.zyklen.sort()
        m.segmente.sort()
    return out


# ── comparison ───────────────────────────────────────────────────────────────


def iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def zuordnen(manuell: list[tuple[float, float]], erkannt: list[tuple[float, float]], min_iou: float = 0.5) -> list[tuple[int, int, float]]:
    """One-to-one pairs (manual index, detected index, IoU), greedy by IoU."""
    kandidaten = sorted(
        ((iou(m, e), i, j) for i, m in enumerate(manuell) for j, e in enumerate(erkannt)), reverse=True
    )
    frei_m, frei_e, paare = set(range(len(manuell))), set(range(len(erkannt))), []
    for w, i, j in kandidaten:
        if w < min_iou:
            break
        if i in frei_m and j in frei_e:
            paare.append((i, j, w))
            frei_m.discard(i)
            frei_e.discard(j)
    return sorted(paare)


def verschwendung_manuell(m: Manuell) -> float | None:
    """Share of the manual cycle time in process steps of the waste class."""
    if not m.segmente or not m.zyklen:
        return None
    total = sum(e - s for s, e in m.zyklen)
    waste = 0.0
    for s, e, typ in m.segmente:
        if STEP_TYPES[typ] != "verschwendung":
            continue
        for zs, ze in m.zyklen:  # only the part inside manual cycles
            waste += max(0.0, min(e, ze) - max(s, zs))
    return waste / total if total else None


def _vk(d: list[float]) -> float | None:
    return float(np.std(d, ddof=1) / np.mean(d)) if len(d) > 1 else None


@dataclass
class VideoErgebnis:
    video: str
    manuell_kein_zyklus: bool
    erkannt: bool
    hinweis: str | None
    anzahl_manuell: int
    anzahl_erkannt: int
    median_manuell_s: float | None
    median_erkannt_s: float | None
    abw_median: float | None  # relative, detected vs manual
    abw_anzahl: float | None  # relative
    falsch_erkannt: int
    verpasst: int
    anteil_falsch: float | None  # of the detected cycles
    anteil_verpasst: float | None  # of the manual cycles
    grenzabweichung_s: float | None  # mean |start| and |end| difference of matched cycles
    vk_manuell: float | None
    vk_erkannt: float | None
    verschwendung_manuell: float | None
    verschwendung_erkannt: float | None
    abw_verschwendung_pp: float | None  # percentage points
    zyklus_richtig: bool  # cycle found / not found as in the manual assessment


def vergleiche(video: str, m: Manuell, zyklen: ZyklusErgebnis, ablauf: AblaufErgebnis | None) -> VideoErgebnis:
    erkannt_z = [(z.start_s, z.ende_s) for z in zyklen.zyklen if z.gueltig and z.art == "zyklus"] if zyklen.erkannt else []
    d_m = [e - s for s, e in m.zyklen]
    d_e = [e - s for s, e in erkannt_z]
    paare = zuordnen(m.zyklen, erkannt_z)
    med_m = float(np.median(d_m)) if d_m else None
    med_e = float(np.median(d_e)) if d_e else None
    grenz = (
        float(np.mean([abs(m.zyklen[i][0] - erkannt_z[j][0]) + abs(m.zyklen[i][1] - erkannt_z[j][1]) for i, j, _ in paare]) / 2)
        if paare else None
    )
    w_m = verschwendung_manuell(m)
    w_e = ablauf.anteile_ablauf["verschwendung"] if ablauf else None
    return VideoErgebnis(
        video=video,
        manuell_kein_zyklus=m.kein_zyklus,
        erkannt=zyklen.erkannt,
        hinweis=zyklen.hinweis,
        anzahl_manuell=len(d_m),
        anzahl_erkannt=len(d_e),
        median_manuell_s=med_m,
        median_erkannt_s=med_e,
        abw_median=(med_e - med_m) / med_m if med_m and med_e else None,
        abw_anzahl=(len(d_e) - len(d_m)) / len(d_m) if d_m else None,
        falsch_erkannt=len(d_e) - len(paare),
        verpasst=len(d_m) - len(paare),
        anteil_falsch=(len(d_e) - len(paare)) / len(d_e) if d_e else None,
        anteil_verpasst=(len(d_m) - len(paare)) / len(d_m) if d_m else None,
        grenzabweichung_s=grenz,
        vk_manuell=_vk(d_m),
        vk_erkannt=zyklen.zykluszeit_vk.wert if zyklen.erkannt else None,
        verschwendung_manuell=w_m,
        verschwendung_erkannt=w_e,
        abw_verschwendung_pp=100 * (w_e - w_m) if w_m is not None and w_e is not None else None,
        zyklus_richtig=zyklen.erkannt != m.kein_zyklus,
    )


# ── targets and summary ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Ziele:
    median: float = 0.10  # STECKBRIEF_MODUL §8.3
    # confirmed on 30.10.2026 (STECKBRIEF_MODUL §8)
    anzahl: float = 0.10
    falsch: float = 0.10
    verschwendung_pp: float = 5.0
    min_videos: int = 3  # fewer videos give no decision


def _ok(x: float | None, grenze: float) -> bool:
    return x is not None and abs(x) <= grenze + 1e-12


def gesamt(ergebnisse: list[VideoErgebnis], ziele: Ziele) -> dict:
    """Summary and the decision per metric group (only when all videos meet the target)."""
    mit_zyklus = [e for e in ergebnisse if not e.manuell_kein_zyklus]
    mit_ablauf = [e for e in ergebnisse if e.abw_verschwendung_pp is not None]

    def entscheidung(videos: list, ok) -> dict:
        n_ok = sum(1 for e in videos if ok(e))
        if len(videos) < ziele.min_videos:
            status = "zu wenige Videos"
        else:
            status = "Ziel erreicht" if n_ok == len(videos) else "Ziel nicht erreicht"
        return {"videos": len(videos), "im_ziel": n_ok, "status": status}

    abs_mean = lambda xs: float(np.mean(np.abs(xs))) if xs else None  # noqa: E731
    n_e = sum(e.anzahl_erkannt for e in mit_zyklus)
    n_m = sum(e.anzahl_manuell for e in mit_zyklus)
    return {
        "videos": len(ergebnisse),
        "zyklus_richtig": sum(e.zyklus_richtig for e in ergebnisse),
        "median": {**entscheidung(mit_zyklus, lambda e: _ok(e.abw_median, ziele.median)),
                   "mittlere_abw": abs_mean([e.abw_median for e in mit_zyklus if e.abw_median is not None])},
        "anzahl": {**entscheidung(mit_zyklus, lambda e: _ok(e.abw_anzahl, ziele.anzahl) and _ok(e.anteil_falsch, ziele.falsch)),
                   "mittlere_abw": abs_mean([e.abw_anzahl for e in mit_zyklus if e.abw_anzahl is not None]),
                   "anteil_falsch": sum(e.falsch_erkannt for e in mit_zyklus) / n_e if n_e else None,
                   "anteil_verpasst": sum(e.verpasst for e in mit_zyklus) / n_m if n_m else None},
        "kein_zyklus": entscheidung([e for e in ergebnisse if e.manuell_kein_zyklus], lambda e: e.zyklus_richtig),
        "verschwendung": {**entscheidung(mit_ablauf, lambda e: _ok(e.abw_verschwendung_pp, ziele.verschwendung_pp)),
                          "mittlere_abw_pp": abs_mean([e.abw_verschwendung_pp for e in mit_ablauf])},
    }


# metrics whose label "Pilotphase" depends on a group (export.PILOTPHASE)
PILOT_GRUPPEN = {
    "median": ["zykluszeit_median_s"],
    "anzahl": ["zyklen_pro_schicht", "zeitanteil_in_zyklen"],
    "verschwendung": ["ablaufschritte"],
}
NICHT_GEPRUEFT = ["zykluszeit_vk", "hoehenzonen", "griffe_ausserhalb_greifraum", "drehung_anteil", "drehungen_pro_zyklus",
                  "verbesserungs_score", "automatisierungs_score"]


# ── report ───────────────────────────────────────────────────────────────────


def _p(x: float | None, vorzeichen: bool = True) -> str:
    if x is None:
        return "k. A."
    s = f"{100 * x:+.1f}" if vorzeichen else f"{100 * x:.1f}"
    return s.replace(".", ",") + " %"


def _s(x: float | None) -> str:
    return "k. A." if x is None else f"{x:.1f}".replace(".", ",") + " s"


def _pp(x: float | None) -> str:
    return "k. A." if x is None else f"{x:+.1f}".replace(".", ",") + " Pp."


def bericht(ergebnisse: list[VideoErgebnis], g: dict, ziele: Ziele, quelle: str, synthetisch: bool = False) -> str:
    z = lambda v: f"{100 * v:.0f}".replace(".", ",")  # noqa: E731
    out = [
        "# Validierung Arbeitsplatz-Steckbrief",
        "",
        f"Stand: {date.today().strftime('%d.%m.%Y')} · erzeugt mit `backend/scripts/validate_steckbrief.py` · Quelle: {quelle}",
        "",
    ]
    if synthetisch:
        out += [
            "> **Prüflauf mit synthetischen Daten, keine Validierung.** Die Videos sind erzeugte Bewegungsdaten mit bekannten",
            "> Zyklen, die „manuellen“ Zeitstempel sind die bekannte Wahrheit mit Zeitversatz wie bei einer Erfassung von Hand.",
            "> Der Lauf zeigt, dass das Skript rechnet, was es soll. Über echte Arbeitsplätze sagt er nichts.",
            "> **Das Label „Pilotphase“ bleibt für alle Kennzahlen**, bis ein Lauf mit echten Videos mit geklärten Nutzungsrechten vorliegt.",
            "",
        ]
    out += [
        "## Ziele",
        "",
        "| Kennzahl | Ziel | Herkunft |",
        "|---|---|---|",
        f"| Median-Zykluszeit | innerhalb ±{z(ziele.median)} % der manuellen Messung | STECKBRIEF_MODUL Abschnitt 8.3 |",
        f"| Anzahl Zyklen | innerhalb ±{z(ziele.anzahl)} %, höchstens {z(ziele.falsch)} % falsch erkannte Zyklen | Abschnitt 8, bestätigt am 30.10.2026 |",
        f"| Zeitanteil Verschwendung | innerhalb ±{str(ziele.verschwendung_pp).replace('.', ',')} Prozentpunkte | Abschnitt 8, bestätigt am 30.10.2026 |",
        "| kein Zyklus | kein Zyklus erkannt, wo von Hand keiner gesehen wird | Abschnitt 8, bestätigt am 30.10.2026 |",
        "",
        f"Eine Entscheidung gibt es ab {ziele.min_videos} Videos je Kennzahl, und nur wenn alle Videos im Ziel liegen.",
        "",
        "## Ergebnis je Video",
        "",
        "| Video | Zyklen von Hand / erkannt | Median von Hand / erkannt | Abweichung Median | Abweichung Anzahl | falsch erkannt | verpasst | Grenzen im Mittel | VK von Hand / erkannt | Verschwendung von Hand / erkannt |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in ergebnisse:
        if e.manuell_kein_zyklus:
            erg = "kein Zyklus erkannt (richtig)" if e.zyklus_richtig else f"{e.anzahl_erkannt} Zyklen erkannt (falsch)"
            out.append(f"| {e.video} | von Hand kein Zyklus · {erg} | | | | | | | | |")
            continue
        med_ok = " ✓" if _ok(e.abw_median, ziele.median) else (" ✗" if e.abw_median is not None else "")
        erkannt = f"{e.anzahl_erkannt}" if e.erkannt else f"0 ({e.hinweis})"
        w = (f"{_p(e.verschwendung_manuell, False)} / {_p(e.verschwendung_erkannt, False)} ({_pp(e.abw_verschwendung_pp)})"
             if e.verschwendung_manuell is not None else "k. A.")
        out.append(
            f"| {e.video} | {e.anzahl_manuell} / {erkannt} | {_s(e.median_manuell_s)} / {_s(e.median_erkannt_s)} | {_p(e.abw_median)}{med_ok} "
            f"| {_p(e.abw_anzahl)} | {e.falsch_erkannt} ({_p(e.anteil_falsch, False)}) | {e.verpasst} ({_p(e.anteil_verpasst, False)}) "
            f"| {_s(e.grenzabweichung_s)} | {_p(e.vk_manuell, False)} / {_p(e.vk_erkannt, False)} | {w} |"
        )
    m, a, k, w = g["median"], g["anzahl"], g["kein_zyklus"], g["verschwendung"]
    out += [
        "",
        "Falsch erkannt: erkannter Zyklus ohne passenden Zyklus von Hand (Überlappung IoU unter 0,5). Verpasst: Zyklus von Hand ohne erkannten. "
        "Grenzen im Mittel: mittlere Abweichung von Anfang und Ende zugeordneter Zyklen. Verschwendung erkannt: aus der Expertenbewertung (review.json), "
        "übertragen auf alle Zyklen; von Hand: Ablaufschritte der CSV mit Standardeinstufung.",
        "",
        "## Zusammenfassung",
        "",
        "| Kennzahl | Videos im Ziel | mittlere Abweichung | Entscheidung |",
        "|---|---|---|---|",
        f"| Median-Zykluszeit | {m['im_ziel']} von {m['videos']} | {_p(m['mittlere_abw'], False)} | {m['status']} |",
        f"| Anzahl Zyklen | {a['im_ziel']} von {a['videos']} | {_p(a['mittlere_abw'], False)}; falsch erkannt {_p(a['anteil_falsch'], False)}, verpasst {_p(a['anteil_verpasst'], False)} | {a['status']} |",
        f"| kein Zyklus | {k['im_ziel']} von {k['videos']} | | {k['status']} |",
        f"| Zeitanteil Verschwendung | {w['im_ziel']} von {w['videos']} | {_pp(w['mittlere_abw_pp'])[1:] if w['mittlere_abw_pp'] is not None else 'k. A.'} | {w['status']} |",
        "",
        "## Label „Pilotphase“",
        "",
        "| Kennzahl im Steckbrief | Label |",
        "|---|---|",
    ]
    for gruppe, felder in PILOT_GRUPPEN.items():
        entfaellt = g[gruppe]["status"] == "Ziel erreicht" and not synthetisch
        for f in felder:
            out.append(f"| `{f}` | {'kann entfallen' if entfaellt else 'bleibt'} |")
    for f in NICHT_GEPRUEFT:
        out.append(f"| `{f}` | bleibt (mit diesem Skript nicht geprüft) |")
    out += [
        "",
        "Das Label entfällt erst, wenn die Entscheidung im Repo umgesetzt ist (`PILOTPHASE` in `backend/app/services/workplace/export.py`, "
        "Hinweise in Dashboard und PDF).",
        "",
        "## So entsteht dieser Bericht",
        "",
        "1. Videos mit geklärten Nutzungsrechten auswählen, möglichst verschiedene Arbeitsplätze (kurze und lange Zyklen, mit Unterbrechungen, "
        "einer ohne wiederkehrenden Zyklus).",
        "2. Von Hand je Video jeden vollständigen Zyklus mit Anfang und Ende in Sekunden erfassen (gleicher Bezugspunkt, z.B. Griff zum neuen Teil). "
        "Unterbrechungen nicht als Zyklus erfassen. Für die Verschwendung zusätzlich die Ablaufschritte mit Typ.",
        "3. Für jedes Video `pose.npz` und, falls bewertet, `review.json` aus `results/{job_id}/` laden, oder das Video selbst neben die CSV legen.",
        "4. `python -m backend.scripts.validate_steckbrief manuell.csv --daten DIR --out docs/validierung_steckbrief.md` (Vorlage für die CSV: `docs/validierung_vorlage.csv`)",
        "",
    ]
    return "\n".join(out)


# ── data loading ─────────────────────────────────────────────────────────────


def finde_daten(daten: Path, video: str) -> tuple[Path | None, Path | None, Path | None]:
    """(pose.npz, review.json, video file) for one video name of the CSV."""
    stem = Path(video).stem
    ordner = daten / video
    if ordner.is_dir() and (ordner / "pose.npz").exists():
        r = ordner / "review.json"
        return ordner / "pose.npz", r if r.exists() else None, None
    npz = daten / f"{stem}.npz"
    review = daten / f"{stem}.review.json"
    review = review if review.exists() else None
    if npz.exists():
        return npz, review, None
    datei = daten / video
    if datei.is_file() and datei.suffix.lower() in VIDEO_ENDUNGEN:
        return None, review, datei
    return None, review, None


def ablauf_aus_review(review: dict | None, zyklen: ZyklusErgebnis) -> AblaufErgebnis | None:
    if not review or not zyklen.erkannt:
        return None
    schritte = [BewerteterSchritt(s["start_phase"], s["ende_phase"], s["typ"], s.get("klasse") or STEP_TYPES[s["typ"]])
                for s in review["segmente"]]
    return transfer(schritte, zyklen)


def auswerten(manuell: dict[str, Manuell], daten: Path, schicht_min: float = 480.0) -> list[VideoErgebnis]:
    ergebnisse = []
    for video, m in sorted(manuell.items()):
        npz, review_pfad, datei = finde_daten(daten, video)
        if npz is not None:
            pose = load_npz(npz.read_bytes())
        elif datei is not None:
            from backend.scripts.plot_cycles import pose_from_video

            pose = pose_from_video(datei, daten / f"{Path(video).stem}.npz")
        else:
            raise FileNotFoundError(f"{video}: weder pose.npz noch Videodatei in {daten}")
        zyklen = detect_cycles(prepare(pose), schicht_min)
        review = json.loads(review_pfad.read_text(encoding="utf-8")) if review_pfad else None
        ergebnisse.append(vergleiche(video, m, zyklen, ablauf_aus_review(review, zyklen)))
    return ergebnisse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Steckbrief-Kennzahlen gegen manuelle Zeitstempel prüfen (STECKBRIEF_MODUL §8).")
    ap.add_argument("csv", type=Path, help="CSV: video,start_s,ende_s,typ")
    ap.add_argument("--daten", type=Path, required=True, help="Ordner mit pose.npz, review.json oder Videos")
    ap.add_argument("--out", type=Path, help="Bericht als Markdown (z.B. docs/validierung_steckbrief.md)")
    ap.add_argument("--json", type=Path, help="Ergebnisse zusätzlich als JSON")
    ap.add_argument("--ziel-median", type=float, default=Ziele.median, help="relativ, Standard 0.10 (Plan)")
    ap.add_argument("--ziel-anzahl", type=float, default=Ziele.anzahl)
    ap.add_argument("--ziel-falsch", type=float, default=Ziele.falsch)
    ap.add_argument("--ziel-verschwendung", type=float, default=Ziele.verschwendung_pp, help="Prozentpunkte")
    ap.add_argument("--min-videos", type=int, default=Ziele.min_videos)
    ap.add_argument("--synthetisch", action="store_true", help="Prüflauf mit erzeugten Daten kennzeichnen")
    a = ap.parse_args(argv)
    ziele = Ziele(a.ziel_median, a.ziel_anzahl, a.ziel_falsch, a.ziel_verschwendung, a.min_videos)
    ergebnisse = auswerten(lese_csv(a.csv), a.daten)
    g = gesamt(ergebnisse, ziele)
    text = bericht(ergebnisse, g, ziele, a.csv.name, a.synthetisch)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    else:
        print(text)
    if a.json:
        a.json.write_text(json.dumps({"videos": [asdict(e) for e in ergebnisse], "gesamt": g, "ziele": asdict(ziele)},
                                     ensure_ascii=False, indent=2), encoding="utf-8")
    for name in ("median", "anzahl", "kein_zyklus", "verschwendung"):
        print(f"{name}: {g[name]['im_ziel']} von {g[name]['videos']} im Ziel, {g[name]['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
