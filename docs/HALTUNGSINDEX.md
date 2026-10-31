# Haltungsindex auf REBA-Basis (1 bis 10)

Stand: 31.10.2026 (Entscheidung G3). Bis dahin hieß der Wert „REBA“.

## Was gemessen wird

Je ausgewertetem Bild (etwa eines pro Sekunde) bestimmt `backend/app/services/analyzer.py` aus den Gelenkpunkten Winkel und ordnet sie nach den Winkelbereichen von REBA (Rapid Entire Body Assessment) Teilwerten zu:

| Region | Winkel | Teilwerte |
|---|---|---|
| Rumpf | Neigung gegen die Senkrechte | 1,0 / 2,5 / 5,5 / 8,0 ab 5°, 20°, 45° |
| Nacken | Rumpfachse gegen Schulter zur Ohrmitte | 1,0 / 3,0 / 6,5 ab 10°, 20° |
| Oberarm | Winkel zum Rumpf (Schulter zur Hüfte) | 1,5 / 3,0 / 5,5 / 8,0 ab 20°, 45°, 90° |
| Unterarm | Beugung im Ellbogen | 1,5 bei 60° bis 100°, sonst 4,5 |
| Knie | Beugung | 1,0 / 3,5 / 6,5 ab 30°, 60° |

Der Index ist das gewichtete Mittel der auf ihr Maximum bezogenen Teilwerte (Rumpf 30 %, Nacken 20 %, linke und rechte Schulter, linkes und rechtes Knie, Unterarm je 10 %), umgerechnet auf 1 bis 10. Aufrechtes Stehen mit hängenden Armen ergibt etwa 3.

Seit dem 31.10.2026 sind Nacken, Oberarm und Unterarm wie in der REBA-Definition gemessen, gleich wie in der Browser-Variante (Repo `motavi`, `src/analysis/reba.ts`). Vorher ergab ein hängender Arm die höchste Oberarmstufe (aufrechtes Stehen etwa 4,6).

## Was er nicht ist

Kein Standard-REBA: Es fehlen die Tabellen A, B und C, Last bzw. Kraft, Griffart, Aktivität und die Handgelenke; die Skala reicht bis 10, nicht bis 15. Ein Vergleich mit manuellen REBA-Bewertungen ist deshalb nur über die Stufen möglich. Standard-REBA kommt mit der Validierung (Entscheidung G3).

## Stufen

Überall gleich: Analyse (`analyzer.stufe`), Ergonomie-Report (`services/pdf.py`), Dashboard (`frontend/src/lib/rebaStufe.ts`), Website (Repo `motavi`, `src/lib/steckbrief.ts`).

| Index | Stufe | Hinweis |
|---|---|---|
| unter 4 | niedrig | derzeit kein Handlungsbedarf |
| 4 bis unter 6 | mittel | Gestaltung prüfen |
| 6 bis unter 8 | hoch | Gestaltung bald verbessern |
| ab 8 | sehr hoch | Gestaltung vorrangig verbessern |

Die Grenzen sind Annahmen (Pilotphase) und werden mit der Validierung geprüft.

## Im Steckbrief (`config/workplace_scoring.json`)

- Belastungsindex: Teil `reba_mittel` mit `null_bei` 3 (etwa aufrechtes Stehen) und `voll_bei` 8 (Beginn „sehr hoch“), Gewicht 0,5.
- Vorrang: ab Index 6, also ab Stufe „hoch“.
- Arbeitsplatz-Check, Frage Haltung: selten 3,0, gelegentlich 5,0, häufig 7,0, ständig 8,5 (je Stufenmitte). „Häufig“ und „ständig“ ergeben damit „vorrangig“, über alle Antwortkombinationen die Hälfte.

Die Feldnamen `reba_score`, `reba_mittel`, `reba_max` bleiben aus Kompatibilitätsgründen (Export-Format 1.0, `docs/steckbrief_schema.json`, dort 1 bis 10).
