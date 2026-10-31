# Scores, Empfehlung, Wirtschaftlichkeit (S4)

Umsetzung von STECKBRIEF_MODUL Abschnitt 4.5 und 5 (Repo `motavi`, `docs/STECKBRIEF_MODUL.md`).

## Einzige Quelle: `config/workplace_scoring.json`

Alles, was bewertet, steht in dieser Datei. Im Code gibt es keine Gewichte, Schwellen, vermeidbaren Anteile oder Regeln.

| Abschnitt | Inhalt |
|---|---|
| `schritt_typen` | Ablaufschritte und Standardeinstufung (auch für die Expertenansicht aus S3) |
| `vermeidbarer_anteil` | je Verschwendungstyp, z.B. Suchen 0,8 |
| `belastung` | Belastungsindex aus Haltungsindex auf REBA-Basis (`docs/HALTUNGSINDEX.md`), Bücken, Überkopf, Drehung |
| `handhabbarkeit` | Handhabbarkeitsindex aus Teilegewicht und größter Kante |
| `verbesserungs_score`, `automatisierungs_score` | Kriterien mit Gewicht und Abbildung auf 0 bis 1 |
| `empfehlung` | Schwellen 50 und 60, Entscheidungstabelle, Texte |
| `vorrang` | Haltungsindex ab 6 (Stufe hoch) |
| `automatisierungstypen` | Regeln in Prüfreihenfolge, Standardbandbreiten für automatisierbaren Anteil und Investition |
| `kundenangaben` | Toleranz der Plausibilitätsprüfung Stück pro Schicht |
| `wirtschaftlichkeit` | Pflichthinweis |

Beim Start prüft `backend/app/services/workplace/scoring_config.py` die Datei: Gewichte je Score in Summe 1, alle vier Kombinationen der Entscheidungstabelle genau einmal, bekannte Typen, Bandbreiten von klein nach groß. Eine fehlerhafte Datei verhindert den Start, statt still falsch zu rechnen. Pfad abweichend über die Umgebungsvariable `WORKPLACE_SCORING_CONFIG`. Das Docker-Image enthält `config/`.

Die Website (Repo `motavi`) liest eine Kopie unter demselben Pfad: `npm run sync:scoring` kopiert sie aus diesem Repo. `test_arbeitsplatz_check.py` hier und `src/lib/scoring.test.ts` dort schlagen fehl, wenn die Kopie abweicht. Nach jeder Änderung an der Datei also im Website-Repo `npm run sync:scoring` ausführen.

**Arbeitsplatz-Check** (`arbeitsplatz_check`): acht Fragen der Website mit je vier Antworten. Jede Antwort setzt Kennzahlen auf einen typischen Wert (z.B. „200 bis 600 Mal“ setzt 400 Zyklen pro Schicht), danach entscheiden dieselben Scores und Regeln wie im Steckbrief. Beim Laden wird geprüft, dass jede Kennzahl bekannt ist und jedes Kriterium beider Scores von einer Frage abgedeckt wird. Über alle 65.536 Antwortkombinationen ergibt der Check Verbessern 35 %, Beibehalten 31 %, Erst verbessern, dann automatisieren 23 %, Automatisieren 11 % (Stand 31.10.2026, Haltungsindex 1 bis 10).

Messschwellen (Ruhe, Gehen, Zyklusdauer, Drehwinkel) stehen weiter beim jeweiligen Messverfahren (`CycleConfig`, `ReachConfig`, `SegmentConfig`, `BelastungConfig`). Sie bestimmen, was gemessen wird, nicht wie es bewertet wird.

## Abbildung auf 0 bis 1

Jedes Kriterium hat `null_bei` und `voll_bei`. Dazwischen linear, außerhalb begrenzt. Ist `null_bei` größer als `voll_bei`, gilt die Abbildung invers (z.B. Varianten: 20 ergibt 0, eine Variante ergibt 1).

Score = 100 × Summe(Gewicht × Teilwert) / Summe der Gewichte mit Wert, kaufmännisch gerundet.

**Fehlende Werte** (Kennzahl fehlt oder ist nicht belastbar, Kundenangabe fehlt): Das Kriterium fällt weg, sein Gewicht verteilt sich auf die übrigen. Der Score ist dann „nicht vollständig“ und nennt die fehlenden Kriterien; die Empfehlung ist „vorläufig“. Liegen weniger als `min_gewicht_vorhanden` vor, ist der Score nicht belastbar und es gibt keine Empfehlung.

**Kein wiederkehrender Zyklus** ist ein Ergebnis (Abschnitt 4.1): Wiederholungen, Gleichförmigkeit und Zeitanteil in Zyklen zählen dann mit Teilwert 0 (`ohne_zyklus`). Damit kommt der Automatisierungs-Score auf höchstens 50 und es gibt nie eine Empfehlung mit Automatisierung. Der Verbesserungs-Score entsteht aus Greifraum und Belastung (genau 50 % Gewicht, deshalb `min_gewicht_vorhanden` 0,5). Ist die Zyklenerkennung dagegen nicht belastbar (zu wenig Bilder mit Person), fallen die Kriterien weg.

## Empfehlung, Vorrang, Typ

- Verbesserungs-Score ab 50 und Automatisierungs-Score ab 60 gelten als hoch (Schwelle eingeschlossen, verglichen mit dem gerundeten Score). Die Tabelle ordnet die vier Empfehlungen zu, alle gleichwertig.
- **Vorrangig** ab Haltungsindex 6 (Stufe hoch), unabhängig von der Empfehlung.
- **Automatisierungstyp** nur bei einer Empfehlung mit Automatisierung. Die Regeln werden in der Reihenfolge der Datei geprüft (spezifisch vor allgemein: Palettieren, Maschinenbeladung, Prüfautomatisierung, Pick and Place). Vorschlag ist der erste Typ, dessen Bedingungen alle erfüllt sind. Fehlt ein Wert (z.B. Teilegewicht), bleibt die Regel offen und blockiert die folgenden nicht. Alle Regeln mit erfüllten und offenen Bedingungen stehen im Steckbrief als Begründung.
- Empfehlung und Typ tragen `status: "vorschlag"`. Die Bestätigung durch den Experten kommt mit der Expertenansicht in S5.

## Wirtschaftlichkeit

```
min_verbesserung       = Summe je Verschwendungstyp (Zeitanteil × mittlere Zyklusdauer × Zyklen pro Schicht / 60 × vermeidbarer Anteil)
euro_verbesserung_jahr = min_verbesserung × Schichten pro Tag × Arbeitstage / 60 × Vollkosten pro Stunde

stunden_auto_jahr = Zykluszeit × Zyklen pro Schicht × Schichten pro Tag × Arbeitstage / 3600 × automatisierbarer Anteil
euro_auto_brutto  = stunden_auto_jahr × Vollkosten pro Stunde
euro_auto_netto   = euro_auto_brutto × (1 − Betriebskostenanteil des Typs)
amortisation      = Investition / euro_auto_netto, als Bandbreite (kleinste Investition / größte Ersparnis bis größte Investition / kleinste Ersparnis)
```

- Verschwendung ist, was der Experte als Verschwendung eingestuft hat. Stuft er z.B. Prüfen als Verschwendung ein, zählt es in die Minuten, ist aber ohne Eintrag in `vermeidbarer_anteil` nicht vermeidbar.
- **Erst verbessern, dann automatisieren:** Die Automatisierung wird auf dem verbesserten Ablauf gerechnet: Zykluszeit × (1 − vermeidbarer Anteil des Zyklus). Die Zyklen pro Schicht bleiben (gleiche Stückzahl). Bei „Automatisieren“ gilt der aktuelle Ablauf.
- Investition: Kundenangabe, sonst Standardbandbreite des Typs.
- Fehlende Kundenangaben werden genannt; Minuten gibt es auch ohne Euro.
- Pflichthinweis: „Grobe Abschätzung, ersetzt kein Angebot.“
- **Betriebskosten:** Wartung, Energie, Programmierung und Betreuung der Anlage kosten einen Teil der eingesparten Personalkosten wieder. Je Typ steht dafür `betriebskosten_anteil` als Bandbreite in der Konfiguration (Pick and Place und Maschinenbeladung 15 bis 25 %, Palettieren 10 bis 20 %, Prüfautomatisierung 20 bis 35 %; Annahmen). Die vorsichtige Grenze kombiniert die kleine Ersparnis mit dem hohen Anteil, die günstige Grenze umgekehrt. Ausgegeben werden Brutto, Betriebskosten und Netto; die Amortisation rechnet mit Netto. Bei der Verbesserung gibt es keinen Abzug, sie ist organisatorisch.

## Kundenangaben (Abschnitt 4.5)

`PUT /api/v1/workplace/{job_id}/inputs`, alle Felder optional:

| Feld | Bereich |
|---|---|
| `teilegewicht_kg` | 0 bis 1000 |
| `abmessungen_cm` | `laenge`, `breite`, `hoehe` |
| `anzahl_varianten` | ab 1 |
| `stueck_pro_schicht` | ab 1, Plausibilitätsprüfung gegen die hochgerechneten Zyklen (Hinweis ab 25 % Abweichung) |
| `schichten_pro_tag` | 1 bis 4 |
| `schichtdauer_min` | 60 bis 720; ersetzt für die Hochrechnung der Zyklen pro Schicht die Dauer aus der Ergonomie-Analyse |
| `arbeitstage_pro_jahr` | 1 bis 366 |
| `vollkosten_euro_pro_stunde` | bis 1000 |
| `besetzung_schwierigkeit` | 1 bis 5 |
| `investition_euro` | `[von, bis]` |

Unbekannte Felder werden abgelehnt (422). Gespeichert in `results/{job_id}/inputs.json` (Löschfrist 365 Tage).

## API

| Methode | Route | Zugriff | Zweck |
|---|---|---|---|
| GET | `/api/v1/workplace/{job_id}` | angemeldet | Steckbrief berechnen, als `results/{job_id}/workplace.json` speichern und zurückgeben |
| PUT | `/api/v1/workplace/{job_id}/inputs` | angemeldet | Kundenangaben speichern, Steckbrief neu berechnen |

404 ohne Pose-Daten; Kundenangaben werden dann nicht gespeichert.

## Drehung (Abschnitt 4.4)

`result.json` enthält keine Drehung. `belastung.py` misst sie aus `pose.npz`: Winkel zwischen Schulter- und Hüftlinie von oben gesehen (x und geschätzte Tiefe z), Drehung ab 30° und mindestens 0,3 s. Ausgabe: Zeitanteil und Drehungen pro Zyklus. Die Tiefe schätzt MediaPipe aus einem 2D-Bild, der Wert ist grob (Pilotphase) und an echten Videos noch nicht geprüft.

## Testprofile

`backend/tests/profiles.py`, erfundene, plausible Arbeitsplätze:

| Profil | Verbesserung | Automatisierung | Empfehlung | Typ |
|---|---|---|---|---|
| Montage (wie Demo in Abschnitt 7) | 55 | 81 | Erst verbessern, dann automatisieren | Pick and Place |
| Rüstplatz, Suchen und Gehen, 40 Varianten | 92 | 32 | Verbessern | keiner |
| schlanker 20-s-Takt, eine Variante | 11 | 87 | Automatisieren | Pick and Place |
| lange, wechselnde Arbeit, wenig Verschwendung | 21 | 19 | Beibehalten | keiner |

Die Startwerte der Konfiguration sind Annahmen. Vor dem Pilotbetrieb an drei bis fünf Arbeitsplätzen gegen die eigene Expertenbewertung prüfen und nachjustieren (Abschnitt 8).
