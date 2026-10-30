# Validierung Arbeitsplatz-Steckbrief

Stand: 30.10.2026 · erzeugt mit `backend/scripts/validate_steckbrief.py` · Quelle: manuell.csv

> **Prüflauf mit synthetischen Daten, keine Validierung.** Die Videos sind erzeugte Bewegungsdaten mit bekannten
> Zyklen, die „manuellen“ Zeitstempel sind die bekannte Wahrheit mit Zeitversatz wie bei einer Erfassung von Hand.
> Der Lauf zeigt, dass das Skript rechnet, was es soll. Über echte Arbeitsplätze sagt er nichts.
> **Das Label „Pilotphase“ bleibt für alle Kennzahlen**, bis ein Lauf mit echten Videos mit geklärten Nutzungsrechten vorliegt.

## Ziele

| Kennzahl | Ziel | Herkunft |
|---|---|---|
| Median-Zykluszeit | innerhalb ±10 % der manuellen Messung | STECKBRIEF_MODUL Abschnitt 8.3 |
| Anzahl Zyklen | innerhalb ±10 %, höchstens 10 % falsch erkannte Zyklen | Vorschlag |
| Zeitanteil Verschwendung | innerhalb ±5,0 Prozentpunkte | Vorschlag |
| kein Zyklus | kein Zyklus erkannt, wo von Hand keiner gesehen wird | Vorschlag |

Eine Entscheidung gibt es ab 3 Videos je Kennzahl, und nur wenn alle Videos im Ziel liegen.

## Ergebnis je Video

| Video | Zyklen von Hand / erkannt | Median von Hand / erkannt | Abweichung Median | Abweichung Anzahl | falsch erkannt | verpasst | Grenzen im Mittel | VK von Hand / erkannt | Verschwendung von Hand / erkannt |
|---|---|---|---|---|---|---|---|---|---|
| kommissionieren_60s.mp4 | 5 / 5 | 57,5 s / 57,3 s | -0,5 % ✓ | +0,0 % | 0 (0,0 %) | 0 (0,0 %) | 4,8 s | 12,7 % / 6,9 % | 45,1 % / 44,2 % (-1,0 Pp.) |
| montage_25s_mit_pause.mp4 | 9 / 9 | 25,3 s / 25,0 s | -1,3 % ✓ | +0,0 % | 0 (0,0 %) | 0 (0,0 %) | 1,7 s | 7,1 % / 6,0 % | 44,5 % / 44,9 % (+0,5 Pp.) |
| nacharbeit_ohne_zyklus.mp4 | von Hand kein Zyklus · kein Zyklus erkannt (richtig) | | | | | | | | |
| takt_12s.mp4 | 15 / 15 | 12,0 s / 12,1 s | +1,3 % ✓ | +0,0 % | 0 (0,0 %) | 0 (0,0 %) | 2,7 s | 1,8 % / 1,9 % | 45,1 % / 45,1 % (+0,1 Pp.) |

Falsch erkannt: erkannter Zyklus ohne passenden Zyklus von Hand (Überlappung IoU unter 0,5). Verpasst: Zyklus von Hand ohne erkannten. Grenzen im Mittel: mittlere Abweichung von Anfang und Ende zugeordneter Zyklen. Verschwendung erkannt: aus der Expertenbewertung (review.json), übertragen auf alle Zyklen; von Hand: Ablaufschritte der CSV mit Standardeinstufung.

## Zusammenfassung

| Kennzahl | Videos im Ziel | mittlere Abweichung | Entscheidung |
|---|---|---|---|
| Median-Zykluszeit | 3 von 3 | 1,0 % | Ziel erreicht |
| Anzahl Zyklen | 3 von 3 | 0,0 %; falsch erkannt 0,0 %, verpasst 0,0 % | Ziel erreicht |
| kein Zyklus | 1 von 1 | | zu wenige Videos |
| Zeitanteil Verschwendung | 3 von 3 | 0,5 Pp. | Ziel erreicht |

## Label „Pilotphase“

| Kennzahl im Steckbrief | Label |
|---|---|
| `zykluszeit_median_s` | bleibt |
| `zyklen_pro_schicht` | bleibt |
| `zeitanteil_in_zyklen` | bleibt |
| `ablaufschritte` | bleibt |
| `zykluszeit_vk` | bleibt (mit diesem Skript nicht geprüft) |
| `hoehenzonen` | bleibt (mit diesem Skript nicht geprüft) |
| `griffe_ausserhalb_greifraum` | bleibt (mit diesem Skript nicht geprüft) |
| `drehung_anteil` | bleibt (mit diesem Skript nicht geprüft) |
| `drehungen_pro_zyklus` | bleibt (mit diesem Skript nicht geprüft) |
| `verbesserungs_score` | bleibt (mit diesem Skript nicht geprüft) |
| `automatisierungs_score` | bleibt (mit diesem Skript nicht geprüft) |

Das Label entfällt erst, wenn die Entscheidung im Repo umgesetzt ist (`PILOTPHASE` in `backend/app/services/workplace/export.py`, Hinweise in Dashboard und PDF).

## So entsteht dieser Bericht

1. Videos mit geklärten Nutzungsrechten auswählen, möglichst verschiedene Arbeitsplätze (kurze und lange Zyklen, mit Unterbrechungen, einer ohne wiederkehrenden Zyklus).
2. Von Hand je Video jeden vollständigen Zyklus mit Anfang und Ende in Sekunden erfassen (gleicher Bezugspunkt, z.B. Griff zum neuen Teil). Unterbrechungen nicht als Zyklus erfassen. Für die Verschwendung zusätzlich die Ablaufschritte mit Typ.
3. Für jedes Video `pose.npz` und, falls bewertet, `review.json` aus `results/{job_id}/` laden, oder das Video selbst neben die CSV legen.
4. `python -m backend.scripts.validate_steckbrief manuell.csv --daten DIR --out docs/validierung_steckbrief.md` (Vorlage für die CSV: `docs/validierung_vorlage.csv`)
