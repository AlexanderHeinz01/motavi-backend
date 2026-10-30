# Kontaktformular der Website (`POST /api/v1/contact`)

Endpunkt für das Formular auf `/pilot` der Website (Repo `motavi`, WEBSITE_PLAN Phase 6). Öffentlich, ohne Anmeldung.

## Anfrage

| Feld | Pflicht | Prüfung |
|---|---|---|
| `zielgruppe` | ja | `hersteller` oder `anbieter` (Robotik-Anbieter oder Integrator) |
| `name` | ja | 2 bis 120 Zeichen |
| `unternehmen` | ja | 2 bis 160 Zeichen |
| `funktion` | nein | bis 120 Zeichen |
| `email` | ja | Form `name@domain.tld`, wird kleingeschrieben |
| `telefon` | nein | Ziffern, Leerzeichen, `+ ( ) / . -` |
| `anzahl_arbeitsplaetze` | nein | 1 bis 100.000 |
| `interesse` | nein | Liste aus `kapazitaet`, `automatisierung`, `gesundheit` |
| `nachricht` | nein | bis 4.000 Zeichen |
| `website` | | Honeypot: Menschen lassen es leer. Ist es gefüllt, antwortet der Endpunkt wie bei Erfolg, speichert aber nichts |

Unbekannte Felder werden abgelehnt (422). Antwort bei Erfolg: `202 {"status": "eingegangen"}`.

## Schutz

- **Rate-Limit:** höchstens `CONTACT_RATE_LIMIT` (5) Anfragen je Client-IP in `CONTACT_RATE_WINDOW_S` (600 s), danach 429. Die IP kommt aus `X-Forwarded-For` (Cloud Run). Das Limit liegt im Arbeitsspeicher je Instanz; bei mehreren Instanzen gilt es je Instanz.
- **Honeypot:** siehe oben.
- Speicherfehler: 503 mit dem Hinweis, per E-Mail zu schreiben.

## Speicherung und Löschung

Firestore, Collection `kontaktanfragen`, je Anfrage ein Dokument mit `eingegangen_am` und `loeschen_am` (= Eingang + `CONTACT_RETENTION_DAYS`, Standard 365 Tage). Damit die Anfragen tatsächlich gelöscht werden, einmalig die TTL-Regel anlegen:

```
gcloud firestore fields ttls update loeschen_am --collection-group=kontaktanfragen --enable-ttl
```

## Benachrichtigung per E-Mail (optional)

Wenn `SMTP_HOST`, `SMTP_FROM` und `CONTACT_NOTIFY_TO` gesetzt sind, geht je Anfrage eine E-Mail an `CONTACT_NOTIFY_TO` (STARTTLS, Port `SMTP_PORT`, Anmeldung mit `SMTP_USER`/`SMTP_PASSWORD`). Antworten gehen an die Absenderadresse der Anfrage. Scheitert der Versand, bleibt die Anfrage gespeichert, der Fehler steht im Log.

## Website

Die Website sendet an `${VITE_API_BASE_URL}/api/v1/contact`. CORS erlaubt derzeit alle Ursprünge (`backend/app/main.py`).
