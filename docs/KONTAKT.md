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

- **Rate-Limit:** höchstens `CONTACT_RATE_LIMIT` (5) Anfragen je Client-IP in `CONTACT_RATE_WINDOW_S` (600 s), danach 429. Die IP ist der Eintrag aus `X-Forwarded-For`, den der Proxy angehängt hat: bei Cloud Run direkt der letzte (`CONTACT_PROXY_HOPS=1`), hinter einem externen Load Balancer der vorletzte (`2`). Die vorderen Einträge kann der Absender frei setzen. IPv6 zählt je /64-Netz. Das Limit liegt im Arbeitsspeicher je Instanz, höchstens 10.000 Schlüssel, und beginnt bei einem Neustart von vorn. Gegen gezielte Angriffe hilft es nicht; dafür bei Bedarf Cloud Armor oder ein Captcha ohne Cookies (offen).
- **Honeypot:** siehe oben.
- Speicherfehler: 503 mit dem Hinweis, per E-Mail zu schreiben.

## Speicherung und Löschung

Firestore, Collection `kontaktanfragen`, je Anfrage ein Dokument mit `eingegangen_am` und `loeschen_am` (= Eingang + `CONTACT_RETENTION_DAYS`, Standard 365 Tage). Damit die Anfragen tatsächlich gelöscht werden, einmalig die TTL-Regel anlegen:

```
gcloud firestore fields ttls update loeschen_am --collection-group=kontaktanfragen --enable-ttl
```

## Benachrichtigung per E-Mail

Wenn `SMTP_HOST`, `SMTP_FROM` und `CONTACT_NOTIFY_TO` gesetzt sind, geht je Anfrage eine kurze Nachricht an `CONTACT_NOTIFY_TO`: Zielgruppe und Dokument-ID in Firestore, **ohne Inhalt der Anfrage** (Entscheidung vom 31.10.2026), damit keine personenbezogenen Daten außerhalb der 365 Tage in Postfächern liegen. Gelesen wird die Anfrage in der Firestore-Konsole. Verbindung mit STARTTLS und Zertifikatsprüfung (Port 587) oder TLS (Port 465), Anmeldung mit `SMTP_USER`/`SMTP_PASSWORD` (Secret). Fehler beim Versand werden geloggt, die Anfrage bleibt gespeichert.

Ohne Benachrichtigung bleiben Anfragen unbemerkt; sie ist deshalb Go-live-Bedingung (Repo `motavi`, `docs/GO_LIVE_CHECKLISTE.md`).

Speicherfehler werden ohne personenbezogene Daten geloggt („Kontaktanfrage konnte nicht gespeichert werden“); dafür eine Benachrichtigung in Cloud Monitoring einrichten (`docs/BETRIEB.md`).

## Website

Die Website sendet an `${VITE_API_BASE_URL}/api/v1/contact`. CORS erlaubt nur die Ursprünge in `CORS_ORIGINS` (Komma-getrennt, z.B. die Website-Domain); im Betrieb startet der Dienst ohne diesen Wert nicht.
