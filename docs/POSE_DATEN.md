# Pose-Daten für das Steckbrief-Modul (`pose.npz`)

Stand: 30.10.2026, Phase S1 aus `docs/STECKBRIEF_MODUL.md` (Repo `motavi`).

## Wozu

Die Analyse-Pipeline (`backend/app/services/analyzer.py`) erkennt die Körperhaltung auf jedem Frame, weil sie jeden Frame anonymisiert. Für die Ergonomie-Auswertung nutzt sie davon nur etwa einen Frame pro Sekunde und verwirft den Rest. Das Steckbrief-Modul braucht für die Zykluserkennung mindestens 10 Hz. Deshalb hält ein Rekorder (`backend/app/services/workplace/pose_store.py`) die Gelenkpunkte fest, statt sie zu verwerfen. `result.json` der Ergonomie-Pipeline ändert sich dadurch nicht (Golden-Test `backend/tests/test_golden_pipeline.py`).

Ein- und ausschalten: `WORKPLACE_POSE_RECORDING` in `backend/app/config.py` (Standard: an).

## Ablage und Löschfrist

- Datei: `results/{job_id}/pose.npz` im selben Bucket wie Video und Ergebnis, geschrieben vor `result.json`.
- **`pose.npz` unterliegt derselben Löschfrist wie das Video.** Wird das Video eines Jobs gelöscht, wird `pose.npz` mit gelöscht.
- Hinweis: Eine automatische Löschung ist im Repo bisher nicht umgesetzt (keine Lifecycle-Regel für den Bucket im Code). Eine Regel muss beide Präfixe abdecken: `uploads/` (Rohvideo, anonymisiertes Video) und `results/` (`result.json`, Einzelbilder, `pose.npz`).

## Inhalt

Nur Koordinaten, keine Bilddaten. Keine Personen-ID, nur die Job-ID.

| Feld | Typ | Bedeutung |
|---|---|---|
| `version` | int16 | Formatversion, derzeit 1 |
| `t` | float32 [F] | Zeitstempel je Frame in Sekunden (float32, weil float16 nach etwa 30 Minuten zu ungenau wäre) |
| `landmarks` | float16 [F, 25, 4] | x, y, z, visibility je Gelenkpunkt; NaN, wenn keine Person erkannt wurde |
| `indices` | int16 [25] | MediaPipe-Index je gespeichertem Gelenkpunkt |
| `names` | str [25] | MediaPipe-Name je gespeichertem Gelenkpunkt |
| `fps` | float32 | Bildrate des Videos |
| `step` | int16 | jeder `step`-te Frame wird gespeichert |
| `width`, `height` | int32 | Videogröße in Pixeln |

- **Rate:** höchstens 15 Hz, `step = ceil(fps / 15)`. Beispiele: 25 fps ergibt 12,5 Hz, 30 fps 15 Hz, 60 fps 15 Hz, 10 fps 10 Hz.
- **Koordinaten:** x und y normiert auf 0 bis 1 der Bildbreite und -höhe, z relative Tiefe im Maßstab von x (MediaPipe). Für Winkel zuerst mit Breite und Höhe multiplizieren (`backend/app/services/workplace/preprocess.py`), sonst sind Winkel bei nicht quadratischen Videos verzerrt.
- **Größe:** unkomprimiert 200 Byte je Frame (25 × 4 × float16) plus 4 Byte Zeitstempel; 10 Minuten bei 15 Hz sind höchstens etwa 1,8 MB, komprimiert weniger.

## Gespeicherte Gelenkpunkte

Augen (MediaPipe 1 bis 6) und Mund (9, 10) werden nicht gespeichert (Datensparsamkeit). Nase und Ohren bleiben für Kopf- und Nackenhaltung.

| Spalte | MediaPipe-Index | Name |
|---|---|---|
| 0 | 0 | nose |
| 1 | 7 | left_ear |
| 2 | 8 | right_ear |
| 3 | 11 | left_shoulder |
| 4 | 12 | right_shoulder |
| 5 | 13 | left_elbow |
| 6 | 14 | right_elbow |
| 7 | 15 | left_wrist |
| 8 | 16 | right_wrist |
| 9 | 17 | left_pinky |
| 10 | 18 | right_pinky |
| 11 | 19 | left_index |
| 12 | 20 | right_index |
| 13 | 21 | left_thumb |
| 14 | 22 | right_thumb |
| 15 | 23 | left_hip |
| 16 | 24 | right_hip |
| 17 | 25 | left_knee |
| 18 | 26 | right_knee |
| 19 | 27 | left_ankle |
| 20 | 28 | right_ankle |
| 21 | 29 | left_heel |
| 22 | 30 | right_heel |
| 23 | 31 | left_foot_index |
| 24 | 32 | right_foot_index |

Die Zuordnung steht zusätzlich in der Datei selbst (`indices`, `names`).

## Lesen

```python
from backend.app.services.workplace.pose_store import load_npz
from backend.app.services.workplace.preprocess import prepare

pose = load_npz(data)          # PoseData
prep = prepare(pose)           # Pixel, Lücken bis 0,5 s gefüllt, geglättet, Hüftmitte als Ursprung, Rumpflänge als Maßstab
wrist = prep.joint("right_wrist")
```
