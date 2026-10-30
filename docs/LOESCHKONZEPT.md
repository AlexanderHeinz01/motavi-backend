# Löschkonzept Analyse-Backend

Stand: 30.10.2026. Gilt für den Bucket der Videoanalyse (`GCS_BUCKET_NAME`, Region europe-west3, Frankfurt).

## Grundsatz

Das Originalvideo zeigt Mitarbeitende erkennbar. Es wird nur so lange gespeichert, wie die Auswertung dauert, und danach sofort gelöscht, auch wenn die Auswertung fehlschlägt. Alles, was länger aufbewahrt wird, ist anonymisiert (Kopfbereich geschwärzt) oder besteht nur aus Koordinaten und Kennzahlen.

## Fristen

| Daten | Ablage | Inhalt | Frist | Umsetzung |
|---|---|---|---|---|
| Originalvideo | `raw/{job_id}/video.mp4` | nicht anonymisiert | bis zum Ende der Auswertung | Code löscht direkt nach der Auswertung, auch im Fehlerfall (`analyzer._delete_raw`); Lifecycle-Regel löscht nach 1 Tag als Sicherheitsnetz |
| Anonymisiertes Video | `results/{job_id}/video_anon.mp4` | Kopfbereich geschwärzt | 30 Tage | Lifecycle-Regel |
| Einzelbilder kritischer Momente | `results/{job_id}/frames/*.jpg` | aus dem anonymisierten Video | 30 Tage | Lifecycle-Regel |
| Pose-Daten | `results/{job_id}/pose.npz` | nur Koordinaten, ohne Augen und Mund | 30 Tage | Lifecycle-Regel |
| Ergebnisse | `results/{job_id}/*.json` (`result.json`, `workplace.json`, `inputs.json`, `review.json`) | Kennzahlen, Angaben zum Arbeitsplatz | 365 Tage | Lifecycle-Regel |

Die Frist zählt ab dem Speichern des Objekts. Google Cloud Storage führt Lifecycle-Regeln mit Verzögerung aus, meist innerhalb eines Tages nach Ablauf der Frist. Ein Originalvideo, dessen Löschung im Code fehlschlägt, ist also spätestens nach etwa zwei Tagen weg.

Weitere Ablagen:

- **Temporäre Dateien** der Auswertung liegen in einem temporären Verzeichnis des Containers und werden am Ende der Auswertung entfernt.
- **Logs** (Cloud Logging) enthalten Job-IDs und Fehlermeldungen, keine Videos oder Koordinaten. Aufbewahrung nach der Standardeinstellung von Cloud Logging.
- **Benutzerkonten** (Firestore) sind nicht Teil dieses Konzepts.

## Altbestand (`uploads/`)

Vor dem 30.10.2026 lagen Originalvideo und anonymisiertes Video unter `uploads/{job_id}/`. Die Lifecycle-Datei enthält dafür zwei Regeln mit denselben Fristen:

- `uploads/…/video.mp4` (Original): 1 Tag
- `uploads/…/video_anon.mp4` (anonymisiert): 30 Tage

**Achtung:** Beim Anwenden der Regeln werden alle Altbestände gelöscht, die älter als die jeweilige Frist sind, also alle Originalvideos unter `uploads/`, die älter als ein Tag sind. Vorher die Bestandsaufnahme ausführen.

## Befehle

Bestandsaufnahme (liest nur, löscht nichts):

```
gcloud auth application-default login
python infra/gcs_inventory.py BUCKET_NAME
```

Lifecycle-Regeln anwenden (`infra/gcs_lifecycle.json`):

```
gcloud storage buckets update gs://BUCKET_NAME --lifecycle-file=infra/gcs_lifecycle.json
```

Prüfen:

```
gcloud storage buckets describe gs://BUCKET_NAME
```

In der Ausgabe steht die Lifecycle-Konfiguration mit den fünf Regeln.

Löschen eines einzelnen Jobs auf Anfrage (z.B. Auskunfts- und Löschersuchen), bis es dafür einen Endpunkt gibt:

```
gcloud storage rm --recursive gs://BUCKET_NAME/raw/JOB_ID gs://BUCKET_NAME/results/JOB_ID
```

## Tests

`backend/tests/test_deletion.py` prüft: Ablage unter `raw/`, Löschung nach erfolgreicher und nach fehlgeschlagener Auswertung, Ablage der Medien unter `results/` und dass `infra/gcs_lifecycle.json` die Fristen dieses Konzepts enthält.
