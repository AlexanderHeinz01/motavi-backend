# Plan: Analyse als Worker mit Cloud Run Jobs (E.3.4)

Stand: 31.10.2026. Noch nicht umgesetzt (Entscheidung: planen, beschreiben, später bauen).

## Problem heute

Die Analyse läuft als FastAPI-BackgroundTask im Webdienst (`routers/upload.py`, `services/analyzer.run_pipeline`).

- Ein Deploy (SIGTERM, 10 s) oder das Herunterskalieren einer Instanz bricht laufende Analysen ab. Bei SIGKILL oder Speichermangel läuft `finally` nicht: Das Originalvideo bleibt bis zur Lifecycle-Regel (1 Tag) liegen, `job.json` bleibt auf `processing`.
- `--concurrency=4` begrenzt Anfragen, nicht Analysen. Mehrere Analysen auf einer Instanz teilen sich 4 GiB und 2 CPU.
- Das Video liegt während der Analyse in `/tmp`, auf Cloud Run also im Arbeitsspeicher.

## Zielbild

1. `POST /upload/{job_id}/start` (und der Start über einen Upload-Link) setzt `job.json` auf `wartet_auf_analyse` und startet eine Ausführung des Cloud Run Jobs `motavi-analyse` mit `JOB_ID` als Umgebungsvariable (`google-cloud-run`, `JobsClient.run_job` mit Overrides). Antwort sofort 202.
2. Der Job nutzt dasselbe Image mit anderem Befehl: `python -m backend.app.worker`. Er lädt das Video aus `raw/`, ruft `analyzer._pipeline_sync` auf, schreibt `result.json` und setzt `job.json` auf `fertig` oder `fehler`. Er löscht das Originalvideo wie heute im `finally`.
3. Ressourcen je Ausführung: 1 Aufgabe, 8 GiB, 4 CPU, Zeitlimit 60 min, 1 Wiederholung. Das Video in einem Volume mit `emptyDir` statt im Arbeitsspeicher.
4. Status: `job.json` in Cloud Storage reicht (eine Schreibstelle je Zustand). Firestore nur, wenn eine Übersicht über viele Jobs nötig wird.
5. Aufräumen: Ein täglicher Cloud Scheduler-Aufruf markiert Jobs, die länger als zwei Stunden auf `wartet_auf_analyse` oder `processing` stehen, als `fehler` und löscht ihr Originalvideo.

## Änderungen

| Stelle | Änderung |
|---|---|
| `backend/app/worker.py` | neu: Einstieg des Jobs |
| `routers/upload.py` `analyse_starten` | Job-Ausführung statt BackgroundTask |
| `services/jobs.py` | Status `wartet_auf_analyse`, `fertig`, `fehler` |
| `cloudbuild.yaml` | zweiter Schritt `gcloud run jobs deploy motavi-analyse` mit demselben Image; Webdienst ohne `--no-cpu-throttling`, mit weniger Speicher |
| Dienstkonto | `roles/run.invoker` auf dem Job für den Webdienst |
| `routers/analysis.py` | Status aus `job.json` statt aus dem Vorhandensein des Originalvideos |

## Aufwand

Etwa ein bis zwei Tage einschließlich Tests (Job-Start gemockt, Worker mit dem Golden-Lauf aus `tests/golden_run.py`).
