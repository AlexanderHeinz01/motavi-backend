# Ablaufschritte und Expertenansicht (S3)

Stand: 30.10.2026. Umsetzung von `docs/STECKBRIEF_MODUL.md` Abschnitt 4.3 (Repo `motavi`). Prinzip: Das Tool schlägt vor, der Experte entscheidet.

## Segmentvorschlag (`backend/app/services/workplace/segments.py`)

1. **Signale:** Geschwindigkeit der Handgelenke und der Hüftmitte in Rumpflängen pro Sekunde, im Bildkoordinatensystem, vorher über etwa 0,3 s geglättet. Gezählt wird die schnellere sichtbare Hand.
2. **Median-Zyklus:** Jeder gültige Zyklus aus der Zykluserkennung (S2) wird auf dasselbe Phasenraster (0 bis 1, 200 Punkte) gebracht; je Phase der Median über alle Zyklen.
3. **Phasen im Median-Zyklus:**
   - **Ortswechsel** (Gehen): Die Hüfte bewegt sich mit mindestens 0,5 Rumpflängen pro Sekunde, mindestens 0,4 s lang. Nur hier schlägt das Tool einen Typ vor („Gehen“).
   - **Ruhe:** Die Hände bewegen sich mit weniger als 0,4 Rumpflängen pro Sekunde. Das kann Fügen, Bearbeiten, Prüfen oder Warten sein; das entscheidet der Experte.
   - **Bewegung:** alles andere. Eine Bewegung wird geteilt, wo die Hand umkehrt (Richtungswechsel ab 100°).
   - Segmente unter 0,4 s gehen im längeren Nachbarn auf.
4. **Bewertung durch den Experten:** Typ je Segment; die Einstufung kommt aus der Tabelle und kann geändert werden. Typen und Standardeinstufung stehen in `config/workplace_scoring.json` (`schritt_typen`).

| Typ | Standardeinstufung |
|---|---|
| Fügen, Bearbeiten | wertschöpfend |
| Greifen, Bringen, Platzieren, Prüfen | notwendig |
| Gehen, Suchen, Warten, Umgreifen | Verschwendung |

5. **Übertragung auf alle Zyklen:** Die bestätigten Segmente gelten für jeden gültigen Zyklus mit demselben Phasenanteil, gestreckt auf die Dauer des jeweiligen Zyklus. Ergebnis: Ablaufschritte mit Anteil und Dauer im Median-Zyklus, Anteile wertschöpfend, notwendig und Verschwendung, Sekunden je Zyklus und Minuten pro Schicht (Sekunden je Zyklus mal Zyklen pro Schicht).

Messschwellen (Ruhe, Gehen, Mindestdauer) in `SegmentConfig`, wie bei Zyklen und Greifraum direkt beim Messverfahren. In `config/workplace_scoring.json` steht alles, was bewertet: Typen und Einstufung, vermeidbare Anteile, Gewichte, Schwellen und Regeln (siehe `docs/SCORING.md`).

## API (nur Berater)

| Methode | Route | Zweck |
|---|---|---|
| GET | `/api/v1/workplace/{job_id}/ablauf` | Zyklen, Median-Zyklus mit Geschwindigkeiten, Segmentvorschlag, gespeicherte Bewertung, übertragenes Ergebnis |
| PUT | `/api/v1/workplace/{job_id}/review` | Bewertung speichern (Segmente lückenlos von 0 bis 1, bekannte Typen und Einstufungen), auf alle Zyklen übertragen |

- Zugriff nur mit Rolle `berater` oder `admin` (`require_berater`): ohne Anmeldung 401, mit anderer Rolle 403 „Nur für angemeldete Berater.“
- Ohne `pose.npz` 404; ohne erkannten Zyklus kann nicht bestätigt werden (409).
- Gespeichert wird `results/{job_id}/review.json` mit Segmenten, Kommentar, `bestaetigt_von` (E-Mail) und `bestaetigt_am`. Löschfrist wie alle JSON-Ergebnisse: 365 Tage (`docs/LOESCHKONZEPT.md`).
- Berater anlegen (Bootstrap, mit Setup-Schlüssel):
  ```
  curl -X POST https://HOST/api/v1/auth/register -H "X-Setup-Key: …" -H "Content-Type: application/json" \
    -d '{"email": "name@example.org", "password": "…", "role": "berater"}'
  ```

## Expertenansicht (`frontend/src/pages/ExpertPage.tsx`)

Route `/app/experte/{job_id}`, nur für Berater (`RequireBerater`); im Dashboard erscheint für Berater der Knopf „Ablauf bewerten“.

- Kopf: Median-Zyklus, gültige Zyklen, Konfidenz, Status (Vorschlag oder bestätigt von wem, wann).
- Zeitleiste des Median-Zyklus: Geschwindigkeit von Hand und Hüfte, darunter die Segmente nach Einstufung (wertschöpfend kräftig, notwendig mittel, Verschwendung schraffiert, nicht zugeordnet leer).
- Tabelle der Segmente: Zeit im Zyklus, Dauer, erkannte Art, Typ und Einstufung zum Auswählen (Hinweis „geändert“, wenn die Einstufung vom Standard abweicht), Teilen und Zusammenführen.
- Anteile im Median-Zyklus live, Kommentar, „Bestätigen und auf alle Zyklen übertragen“ (erst aktiv, wenn jedes Segment zugeordnet ist), danach das übertragene Ergebnis.

## Bekannte Grenzen

- Die Übertragung ist proportional. Weicht ein einzelner Zyklus in der Reihenfolge ab (z.B. zusätzliches Suchen), bildet das die Übertragung nicht ab; dafür bräuchte es eine Ausrichtung je Zyklus.
- Ruhe ist nicht gleich Warten: Feine Arbeit mit wenig Handbewegung (Fügen, Prüfen) sieht in der Geschwindigkeit wie Ruhe aus. Deshalb schlägt das Tool dort keinen Typ vor.
- Die Expertenansicht zeigt kein Video, nur Signale. Ein anonymisiertes Standbild je Segment wäre eine sinnvolle Ergänzung.
