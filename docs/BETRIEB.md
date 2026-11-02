# Betrieb des Backends

Stand: 31.10.2026. Cloud Run in `europe-west3` (Frankfurt), Deployment über `cloudbuild.yaml`. Die Befehle führt eine Person mit Projekt-Rechten aus; `PROJECT_ID`, `BUCKET_NAME` und `APP_DOMAIN` ersetzen.

## Was der Dienst ist

- **Internes Werkzeug** für das Motavi-Team: Anmeldung über Firebase (seit 02.11.2026), Dashboard mit allen Jobs (`/app/jobs`), Upload und Upload-Links (`/app`), Expertenansicht, Steckbrief, Zugänge (`/app/zugaenge`, nur Admins). Keine Selbstbedienung für Kunden (Entscheidung G2 vom 31.10.2026). Die Website verlinkt das Werkzeug über die Schaltfläche „Anmelden“ (Repo `motavi`, `APP_URL` in `src/content/site.ts`).
- **Upload-Seite für Kunden** unter `/hochladen/{token}`: Das Team erstellt je Arbeitsplatz einen Link (Upload-Zeitraum `UPLOAD_LINK_DAYS`, Standard 14 Tage, ein Video). Der Kunde sieht keine Ergebnisse.
- **Kontaktformular** der Website: `POST /api/v1/contact` (`docs/KONTAKT.md`).

Zugriff: Jede Route zu einem Job verlangt die Anmeldung. Das Team (Rollen `berater`, `admin`) sieht alle Jobs, andere Nutzer nur selbst angelegte (`results/{job_id}/job.json`, `backend/app/services/jobs.py`). Einzelbilder werden über Links ausgeliefert, die 15 Minuten gelten.

## Einmalige Einrichtung

### 1. Dienstkonto ohne Schlüssel

```
gcloud iam service-accounts create motavi-backend --display-name="Motavi Backend"
SA=motavi-backend@PROJECT_ID.iam.gserviceaccount.com

# Bucket: lesen, schreiben, überschreiben, löschen (ohne Löschrecht scheitert das Löschen des Originalvideos)
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME --member=serviceAccount:$SA --role=roles/storage.objectUser
# Upload-Sitzungen anlegen braucht zusätzlich nichts; Signieren von URLs wird nicht verwendet
# Firestore: Benutzer und Kontaktanfragen
gcloud projects add-iam-policy-binding PROJECT_ID --member=serviceAccount:$SA --role=roles/datastore.user
# Secrets
for s in JWT_SECRET GCS_BUCKET_NAME; do
  gcloud secrets add-iam-policy-binding $s --member=serviceAccount:$SA --role=roles/secretmanager.secretAccessor
done
```

Cloud Build braucht für das Deployment: `roles/run.admin` (oder `run.developer`), `roles/iam.serviceAccountUser` auf `$SA` und `roles/artifactregistry.writer`.

Danach den alten Schlüssel aus dem Dienst entfernen und löschen: `gcloud run services update motavi-backend --region=europe-west3 --remove-secrets=GCP_SERVICE_ACCOUNT_KEY`, anschließend den Schlüssel in IAM löschen.

### 2. Secrets

```
openssl rand -base64 48 | gcloud secrets create JWT_SECRET --data-file=-
printf BUCKET_NAME | gcloud secrets create GCS_BUCKET_NAME --data-file=-
# erst wenn E-Mail-Benachrichtigung eingerichtet wird:
printf 'PASSWORT' | gcloud secrets create SMTP_PASSWORD --data-file=-
```

`--set-secrets` in `cloudbuild.yaml` ersetzt bei jedem Deploy **alle** Secrets des Dienstes. Deshalb steht die vollständige Liste in der Substitution `_SECRETS` des Build-Triggers. Mit E-Mail: `JWT_SECRET=JWT_SECRET:latest,GCS_BUCKET_NAME=GCS_BUCKET_NAME:latest,SMTP_PASSWORD=SMTP_PASSWORD:latest`.

### 3. Substitutionen im Build-Trigger

| Substitution | Wert |
|---|---|
| `_PUBLIC_APP_URL` | https-Adresse des Dienstes, z.B. `https://APP_DOMAIN` (für Upload-Links) |
| `_CORS_ORIGINS` | Adresse der Website, mehrere mit Komma |
| `_SECRETS` | siehe oben |
| `_SMTP_HOST`, `_SMTP_FROM`, `_CONTACT_NOTIFY_TO` | E-Mail-Benachrichtigung (Go-live-Bedingung) |
| `_FIREBASE_PROJECT_ID`, `_FIREBASE_API_KEY`, `_FIREBASE_AUTH_DOMAIN`, `_FIREBASE_APP_ID`, `_FIREBASE_PROVIDERS`, `_ADMIN_EMAILS` | Anmeldung mit Firebase (Abschnitt 3a) |

Mit `APP_ENV=production` startet der Dienst nicht, wenn `JWT_SECRET` kürzer als 32 Byte ist oder `PUBLIC_APP_URL`, `CORS_ORIGINS` bzw. `FIREBASE_PROJECT_ID` fehlen (`backend/app/main.py`).

### 3a. Anmeldung mit Firebase

1. Firebase-Konsole, Authentication, **Sign-in method**: die gewünschten Anbieter aktivieren (E-Mail/Passwort, Google, Microsoft).
2. Authentication, **Settings, Authorized domains**: die Adresse des Dienstes eintragen (Cloud-Run-Adresse oder eigene Domain, ohne `https://`).
3. Projekteinstellungen, **Allgemein, Meine Apps**: eine Web-App anlegen, falls noch keine da ist. Aus der Konfiguration `apiKey`, `authDomain`, `projectId` und `appId` in die Substitutionen `_FIREBASE_API_KEY`, `_FIREBASE_AUTH_DOMAIN`, `_FIREBASE_PROJECT_ID` und `_FIREBASE_APP_ID` übernehmen. Diese Werte sind nicht geheim.
4. `_FIREBASE_PROVIDERS` auf die aktivierten Anbieter setzen, z.B. `password,google`. `_ADMIN_EMAILS` auf Ihre eigene Adresse: Damit kommen Sie als Admin hinein und geben unter **Zugänge** weitere Personen frei.
5. Bei E-Mail und Passwort: Konten legen Sie in der Firebase-Konsole an (Authentication, Users, Add user). Beim ersten Anmelden bekommt die Person eine E-Mail zur Bestätigung der Adresse. Bei Google und Microsoft ist kein Konto nötig.
6. Empfohlen bei E-Mail und Passwort: die Selbstregistrierung abschalten, soweit die Konsole das anbietet (Authentication, Settings, User actions). Nötig ist es nicht: Ohne Eintrag unter **Zugänge** kommt niemand hinein.

Wer Zugang hat, entscheidet nur das Backend: gültiges Firebase-Token des Projekts, bestätigte E-Mail-Adresse und ein Eintrag in Firestore `users` mit Rolle `user`, `berater` oder `admin` (oder die Adresse steht in `ADMIN_EMAILS`). Mit `FIREBASE_PROJECT_ID` sind die frühere Passwort-Anmeldung (`/auth/login`) und `/auth/register` abgeschaltet.

### 4. Bucket

```
# Lifecycle (docs/LOESCHKONZEPT.md)
gcloud storage buckets update gs://BUCKET_NAME --lifecycle-file=infra/gcs_lifecycle.json
# Soft Delete und Versionierung aus (Entscheidung vom 31.10.2026)
gcloud storage buckets update gs://BUCKET_NAME --clear-soft-delete
gcloud storage buckets update gs://BUCKET_NAME --no-versioning
# Browser-Upload direkt in den Bucket: APP_DOMAIN in infra/gcs_cors.json eintragen
gcloud storage buckets update gs://BUCKET_NAME --cors-file=infra/gcs_cors.json
# prüfen
gcloud storage buckets describe gs://BUCKET_NAME --format="yaml(lifecycle,soft_delete_policy,versioning,cors_config,location)"
```

### 5. Firestore

TTL für Kontaktanfragen (`docs/KONTAKT.md`), Region prüfen (soll `europe-west3` sein), Point-in-Time-Recovery und Sicherungen prüfen (`docs/LOESCHKONZEPT.md`).

### 6. Benachrichtigungen in Cloud Monitoring

Log-basierte Benachrichtigungen auf:

- `"Kontaktanfrage konnte nicht gespeichert werden"` (Anfrage verloren)
- `"Deleting the raw video failed"` (Originalvideo nicht gelöscht, die Lifecycle-Regel greift erst nach einem Tag)
- `"Pipeline failed"`

## Umgebungsvariablen

| Variable | Zweck | Standard |
|---|---|---|
| `APP_ENV` | `production` schaltet die Startprüfung ein | `dev` |
| `GCS_BUCKET_NAME` | Bucket (Secret) | `motavi-videos` |
| `FIREBASE_PROJECT_ID` | Firebase-Projekt der Anmeldung; in Produktion Pflicht | leer (frühere Passwort-Anmeldung) |
| `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_APP_ID` | Web-Konfiguration für die Anmeldeseite (nicht geheim) | leer |
| `FIREBASE_PROVIDERS` | angezeigte Anmeldearten: `password`, `google`, `microsoft` | `password,google` |
| `ADMIN_EMAILS` | immer Admin, kommagetrennt | leer |
| `JWT_SECRET` | signiert Upload-Links und Bildlinks (Secret, mindestens 32 Byte) | leer |
| `JWT_EXPIRE_MINUTES` | Gültigkeit der Anmeldung | 1440 |
| `SETUP_KEY` | erlaubt `POST /auth/register`; leer schaltet es ab (nur zum Anlegen von Konten setzen) | leer |
| `PUBLIC_APP_URL` | Adresse für Upload-Links | leer |
| `CORS_ORIGINS` | erlaubte Ursprünge, Komma-getrennt | leer (lokal: alle) |
| `UPLOAD_MAX_BYTES` | größtes Video | 1 GiB |
| `UPLOAD_LINK_DAYS` | Gültigkeit der Upload-Links | 14 |
| `MODEL_DIR` | MediaPipe-Modelle; im Image `/app/models` | `/tmp/motavi-models` |
| `ANALYSE_MIN_ERKENNUNG` | Anteil der Bilder mit Person, darunter Fehlermeldung statt Ergebnis | 0,5 |
| `CONTACT_RATE_LIMIT`, `CONTACT_RATE_WINDOW_S`, `CONTACT_PROXY_HOPS`, `CONTACT_RETENTION_DAYS` | Kontaktformular (`docs/KONTAKT.md`) | 5, 600, 1, 365 |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `CONTACT_NOTIFY_TO` | Benachrichtigung | leer, 587 |
| `WORKPLACE_POSE_RECORDING`, `WORKPLACE_SCORING_CONFIG` | Steckbrief-Modul (`docs/SCORING.md`) | an, `config/workplace_scoring.json` |
| `GCP_SERVICE_ACCOUNT_KEY`, `GOOGLE_APPLICATION_CREDENTIALS` | nur lokal oder ohne angehängtes Dienstkonto | leer |

## Zugänge vergeben

Mit Firebase (seit 02.11.2026): Admins geben im Werkzeug unter **Zugänge** eine E-Mail-Adresse mit Rolle frei. Rollen:

- `berater`: alle Jobs, Expertenansicht, Upload-Links;
- `admin`: zusätzlich Zugänge;
- `user`: nur selbst angelegte Jobs.

Passwort vergessen und Bestätigung der Adresse übernimmt Firebase. Der erste Admin steht in `ADMIN_EMAILS`.

Ohne Firebase (nur lokal): `POST /api/v1/auth/register` mit dem Kopf `X-Setup-Key`.

## Bekannte Grenzen

- Die Analyse läuft als Hintergrundaufgabe im Webdienst. Ein Deploy oder das Herunterskalieren bricht laufende Analysen ab. Geplant ist ein Worker mit Cloud Run Jobs (`docs/WORKER.md`).
- Das Rate-Limit des Kontaktformulars und der Anmeldung liegt im Arbeitsspeicher je Instanz.
