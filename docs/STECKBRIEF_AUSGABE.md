# Steckbrief: Dashboard, PDF, Export, Expertenbestätigung (S5)

Umsetzung von STECKBRIEF_MODUL Abschnitt 6 (Repo `motavi`, `docs/STECKBRIEF_MODUL.md`).

## Dashboard-Tab „Steckbrief“

`/app/dashboard/{job_id}?tab=steckbrief`, neben „Ergonomie“, gleiches dunkles Designsystem (`frontend/src/components/SteckbriefTab.tsx`).

- **Kopf:** Empfehlung als großes Label mit einem Satz Erklärung, Status (Vorschlag oder vom Experten bestätigt, bei Änderung mit dem ursprünglichen Vorschlag) und gegebenenfalls „Vorrangig“. Darunter „Ausschlaggebend“: bis zu drei Messwerte als ganze Aussage, z.B. „22 % der Zykluszeit sind Verschwendung“. Bei Automatisierung der Typ mit dem Zusatz „nur der Typ, keine Herstellerempfehlung“.
- **Bewertung:** beide Scores als Balken mit Schwellenmarke. Kriterien ohne Wert werden genannt.
- **Kennzahlen, Ablaufschritte, Greifraum:** mit Hinweis „Pilotphase“; nicht belastbare Werte als „nicht belastbar messbar“.
- **Wirtschaftlichkeit:** Verbessern (Minuten, Euro) und Automatisieren (Grundlage, Stunden, Netto-Ersparnis, Betriebskosten, Investition, Amortisation), Pflichthinweis. Fehlende Angaben werden genannt.
- **Angaben zum Arbeitsplatz:** Formular für die Kundenangaben (§4.5); Speichern berechnet den Steckbrief neu.
- **PDF-Steckbrief und JSON-Export** als Buttons (Download mit Anmeldung).

Alle vier Empfehlungen sehen gleich aus: Sie sind gleichwertige Ergebnisse, keine ist farblich als gut oder schlecht markiert. Verschwendung ist schraffiert, nie nur farbig.

## PDF-Steckbrief (`GET /api/v1/workplace/{job_id}/pdf`)

Zwei Seiten A4, druckfreundlich auf Weiß (`backend/app/services/workplace/pdf_steckbrief.py`), ergänzt den 4-seitigen Report.

| Seite | Inhalt |
|---|---|
| 1 | Arbeitsplatz, Empfehlung mit Erklärung und Status, Vorrang, Ausschlaggebend, beide Scores mit Schwelle, Automatisierungstyp, Kennzahlen Zyklus und Belastung |
| 2 | Ablaufschritte (Balken und Tabelle, Anteile und Minuten je Klasse), Arbeitshöhen und Greifraum, Wirtschaftlichkeit mit Pflichthinweis, Hinweise |

Ein Test sichert genau zwei Seiten für alle vier Empfehlungen und die Randfälle (kein Zyklus, keine Ablaufschritte, keine Kundenangaben).

## JSON-Export (`GET /api/v1/workplace/{job_id}/export`)

Format `motavi-arbeitsplatz-steckbrief`, Version 1.0, Schema in `docs/steckbrief_schema.json` (JSON Schema 2020-12).

- Pflichtfelder sind die Felder des Demo-Formats aus Abschnitt 7; die Demo-Dateien der Website (`src/content/demo/*.json`) sind gültige Exporte mit `"beispiel": true`.
- Zusätzlich: Status der Empfehlung und Vorschlag des Tools, Gründe, Vorrang, Belastungsanteile, Typ und Wirtschaftlichkeit, Kundenangaben, Qualität je Kennzahl, Liste der Kennzahlen in der Pilotphase, Hinweise, Pflichthinweis.
- Nicht belastbare Werte sind `null`, der Grund steht unter `qualitaet`.
- Herstellerneutral: nur Automatisierungstypen; weitere Felder sind nicht erlaubt (`additionalProperties: false`).
- Keine Personendaten: keine Mitarbeiterangaben, keine E-Mail-Adresse des Beraters.

Tests prüfen die Exporte aller Testprofile und, wenn das Repo `motavi` daneben ausgecheckt ist, die Demo-Dateien gegen das Schema.

## Expertenbestätigung von Empfehlung und Typ (`PUT /api/v1/workplace/{job_id}/empfehlung`, nur Berater)

In der Expertenansicht unter den Ablaufschritten: vier gleichwertige Empfehlungen zur Auswahl (der Vorschlag ist markiert), Automatisierungstyp nur bei Empfehlung mit Automatisierung (auch „offen lassen“), Kommentar.

- Gespeichert in `results/{job_id}/empfehlung.json` mit Bearbeiter, Zeitpunkt und dem Vorschlag zu diesem Zeitpunkt (Löschfrist 365 Tage wie alle JSON-Ergebnisse).
- Die Entscheidung des Experten gilt im Steckbrief, in PDF und Export; der Vorschlag des Tools bleibt sichtbar. Die Wirtschaftlichkeit folgt der Entscheidung (z.B. Automatisierung auf dem verbesserten Ablauf mit dem gewählten Typ).
- Ändert sich der Vorschlag später (neue Ablaufschritte oder Angaben), erscheint der Hinweis, die Empfehlung erneut zu prüfen.
- 422 bei einem Typ zu einer Empfehlung ohne Automatisierung oder einem unbekannten Typ.

## Zugriff

| Route | Zugriff |
|---|---|
| `GET /workplace/{job_id}`, `/pdf`, `/export`, `PUT /inputs` | angemeldet |
| `GET /ablauf`, `PUT /review`, `PUT /empfehlung` | Berater und Admin |
