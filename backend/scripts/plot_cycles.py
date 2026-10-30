"""Detected cycles of one video as a PNG diagram (S2, for checking by eye).

    python -m backend.scripts.plot_cycles VIDEO.mp4 --out zyklen.png
    python -m backend.scripts.plot_cycles pose.npz --out zyklen.png
    python -m backend.scripts.plot_cycles VIDEO.mp4 --pose-out pose.npz   # keep the pose for later runs

With a video, the pose is detected like in the analysis pipeline
(MediaPipe Pose Landmarker heavy, image mode) at up to 15 Hz. With a
pose.npz from the bucket the detection is skipped. Needs matplotlib
(requirements-dev.txt). Runs locally, nothing is uploaded.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from backend.app.services.workplace.cycles import ZyklusErgebnis, detect_cycles
from backend.app.services.workplace.pose_store import PoseRecorder, load_npz
from backend.app.services.workplace.preprocess import prepare
from backend.app.services.workplace.quality import Kennzahl
from backend.app.services.workplace.reach import ZONEN, ZONEN_TEXT, GreifraumErgebnis, analyse_reach

# Motavi data colours on light ground (DESIGN_BRIEF §3)
DATA = "#007A99"
RISK = "#C62E3A"
GAIN = "#15803D"
MUTED = "#5B616E"
TEXT = "#1A1A1A"
BORDER = "#E4E6EB"


def pose_from_video(path: Path, pose_out: Path | None = None):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions
    from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions

    from backend.app.services import analyzer

    analyzer._ensure_model()
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    rec = PoseRecorder()
    rec.start(fps, int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    landmarker = PoseLandmarker.create_from_options(
        PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(analyzer._MODEL_PATH)), running_mode=vision.RunningMode.IMAGE)
    )
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % rec._step == 0:  # only the frames the recorder keeps
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            rec.add(i, landmarker.detect(image))
        i += 1
    cap.release()
    landmarker.close()
    data = rec.to_npz_bytes()
    if pose_out:
        pose_out.write_bytes(data)
    return load_npz(data)


def fmt(k: Kennzahl, scale: float = 1.0, digits: int = 1, unit: str = "") -> str:
    if not k.belastbar or k.wert is None:
        return f"{k.anzeige}"
    v = f"{k.wert * scale:.{digits}f}".replace(".", ",")
    return f"{v}{unit}  (Qualität {k.qualitaet:.2f})".replace(".", ",")


def plot(z: ZyklusErgebnis, g: GreifraumErgebnis, title: str, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(13, 9), dpi=120)
    grid = fig.add_gridspec(3, 3, height_ratios=[1.3, 1, 1], hspace=0.55, wspace=0.35)
    ax1 = fig.add_subplot(grid[0, :])
    ax2 = fig.add_subplot(grid[1, :2])
    ax3 = fig.add_subplot(grid[2, :2])
    ax4 = fig.add_subplot(grid[1:, 2])

    # 1. signal with cycles
    ax1.plot(z.t, z.signal, color=TEXT, lw=0.8)
    for k, c in enumerate(z.zyklen):
        if c.art == "unterbrechung":
            ax1.axvspan(c.start_s, c.ende_s, color=MUTED, alpha=0.15, hatch="//", lw=0)
        elif c.gueltig:
            ax1.axvspan(c.start_s, c.ende_s, color=DATA, alpha=0.10 if k % 2 else 0.20, lw=0)
        else:
            ax1.axvspan(c.start_s, c.ende_s, color=RISK, alpha=0.12, lw=0)
        ax1.axvline(c.start_s, color=DATA if c.gueltig else MUTED, lw=0.8)
    status = "Zyklen erkannt" if z.erkannt else (z.hinweis or "kein Zyklus")
    ax1.set_title(f"{title}: {status}", loc="left", fontsize=12, color=TEXT)
    ax1.set_xlabel("Zeit (s)")
    ax1.set_ylabel("Merkmal (1. Hauptkomponente)")
    ax1.text(0.995, 1.02, "blau: gültiger Zyklus · rot: Ausreißer · grau schraffiert: Unterbrechung",
             transform=ax1.transAxes, ha="right", fontsize=8, color=MUTED)

    # 2. autocorrelation
    if len(z.acf) > 1:
        ax2.plot(z.acf_lags_s, z.acf, color=DATA, lw=1)
    if z.periode_s:
        ax2.axvline(z.periode_s, color=TEXT, ls="--", lw=1)
        ax2.text(z.periode_s, ax2.get_ylim()[1], f" Periode {z.periode_s:.1f} s".replace(".", ","), va="top", fontsize=9)
    ax2.set_title(f"Autokorrelation (Periodizität {z.periodizitaet:.2f})".replace(".", ","), loc="left", fontsize=10)
    ax2.set_xlabel("Verschiebung (s)")

    # 3. cycle durations
    cyc = [c for c in z.zyklen if c.art == "zyklus"]
    if cyc:
        ax3.bar(range(1, len(cyc) + 1), [c.dauer_s for c in cyc], color=[DATA if c.gueltig else RISK for c in cyc])
        if z.zykluszeit_median.wert:
            ax3.axhline(z.zykluszeit_median.wert, color=TEXT, ls="--", lw=1)
    else:
        ax3.text(0.5, 0.5, z.hinweis or "keine Zyklen", ha="center", va="center", transform=ax3.transAxes, color=MUTED)
        ax3.set_xticks([]); ax3.set_yticks([])
    ax3.set_title("Zyklusdauern (rot: Ausreißer)", loc="left", fontsize=10)
    ax3.set_xlabel("Zyklus")
    ax3.set_ylabel("s")

    # 4. metrics and reach
    ax4.axis("off")
    lines = [
        "Zyklen",
        f"Median: {fmt(z.zykluszeit_median, unit=' s')}",
        f"Schwankung (VK): {fmt(z.zykluszeit_vk, 100, 0, ' %')}",
        f"Zyklen pro Schicht: {fmt(z.zyklen_pro_schicht, digits=0)}",
        f"Zeitanteil in Zyklen: {fmt(z.zeitanteil_in_zyklen, 100, 0, ' %')}",
        f"gültig: {z.anzahl_gueltig}, Konfidenz {z.konfidenz:.2f}".replace(".", ","),
        "",
        "Greifraum (relativ, 2D)",
        *[f"{ZONEN_TEXT[n]}: {fmt(g.hoehenzonen[n], 100, 0, ' %')}" for n in ZONEN],
        f"Griffe außerhalb: {fmt(g.griffe_ausserhalb, 100, 0, ' %')}",
        f"Griffe erkannt: {g.anzahl_griffe}",
    ]
    ax4.text(0, 1, "\n".join(lines), va="top", fontsize=9, family="monospace", color=TEXT, linespacing=1.6)

    for ax in (ax1, ax2, ax3):
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(BORDER)
        ax.spines["bottom"].set_color(BORDER)
        ax.tick_params(colors=MUTED, labelsize=8)
    fig.savefig(out, bbox_inches="tight", facecolor="white")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", type=Path, help="video file or pose.npz")
    p.add_argument("--out", type=Path, default=Path("zyklen.png"))
    p.add_argument("--shift-min", type=float, default=480.0)
    p.add_argument("--pose-out", type=Path, help="save the detected pose as pose.npz")
    a = p.parse_args()
    pose = load_npz(a.input.read_bytes()) if a.input.suffix == ".npz" else pose_from_video(a.input, a.pose_out)
    prep = prepare(pose)
    z = detect_cycles(prep, a.shift_min)
    g = analyse_reach(prep)
    plot(z, g, a.input.name, a.out)
    med = z.zykluszeit_median
    print(f"{a.input.name}: {'erkannt' if z.erkannt else z.hinweis}; Median {med.anzeige}; gültige Zyklen {z.anzahl_gueltig}; Diagramm {a.out}")


if __name__ == "__main__":
    main()
