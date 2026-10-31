# Löschkonzept Analyse-Backend

Stand: 31.10.2026 (kein Video mehr aufbewahrt, Soft Delete, eingefrorener Steckbrief). Gilt für den Bucket der Videoanalyse (`GCS_BUCKET_NAME`, Region europe-west3, Frankfurt).

## Grundsatz

Das Originalvideo zeigt Mitarbeitende erkennbar. Es wird nur so lange gespeichert, wie die Auswertung dauert, und danach sofort gelöscht, auch wenn die Auswertung fehlschlägt. Ein Video wird seit dem 31.10.2026 nicht mehr aufbewahrt. Länger gespeichert werden nur drei Standbilder, auf denen Köpfe und Gesichter aller erkannten Personen großzügig geschwärzt sind (Bilder ohne erkannte Person werden verworfen), sowie Koordinaten und Kennzahlen.

## Fristen

| Daten | Ablage | Inhalt | Frist | Umsetzung |
|---|---|---|---|---|
| Originalvideo | `raw/{job_id}/video.mp4` | nicht anonymisiert | bis zum Ende der Auswertung | Code löscht direkt nach der Auswertung, auch im Fehlerfall (`analyzer._delete_raw`); Lifecycle-Regel löscht nach 1 Tag als Sicherheitsnetz |
| Einzelbilder kritischer Momente | `results/{job_id}/frames/*.jpg` | drei Standbilder aus dem Original, Köpfe und Gesichter aller Personen geschwärzt (`analyzer._schwaerzen`) | 30 Tage | Lifecycle-Regel |
| Pose-Daten | `results/{job_id}/pose.npz` | nur Koordinaten, ohne Augen und Mund | 30 Tage | Lifecycle-Regel |
| Job | `results/{job_id}/job.json` | wer den Job angelegt hat (E-Mail des Teammitglieds), Quelle, Angaben zum Arbeitsplatz, Status | 365 Tage | Lifecycle-Regel |
| Ergebnisse | `results/{job_id}/*.json` (`result.json`, `inputs.json`, `review.json`, `empfehlung.json`, `steckbrief.json`) | Kennzahlen, Angaben zum Arbeitsplatz; `review.json` und `empfehlung.json` enthalten die E-Mail des bestätigenden Beraters (`bestaetigt_von`) | 365 Tage | Lifecycle-Regel |

**Steckbrief:** Ohne Bestätigung wird er bei jedem Abruf aus `pose.npz` berechnet und nicht gespeichert; nach 30 Tagen ist er dann nicht mehr abrufbar. Nach der Bestätigung durch den Experten wird er als `steckbrief.json` eingefroren und von dort ausgeliefert, unabhängig von `pose.npz`. Ein Abruf schreibt nichts, die 365 Tage zählen ab der letzten Änderung durch das Team.

Die Frist zählt ab dem Speichern des Objekts. Google Cloud Storage führt Lifecycle-Regeln mit Verzögerung aus, meist innerhalb eines Tages nach Ablauf der Frist. Ein Originalvideo, dessen Löschung im Code fehlschlägt, ist also spätestens nach etwa zwei Tagen weg.

Weitere Ablagen:

- **Temporäre Dateien** der Auswertung liegen in einem temporären Verzeichnis des Containers und werden am Ende der Auswertung entfernt.
- **Logs** (Cloud Logging) enthalten Job-IDs und Fehlermeldungen, keine Videos oder Koordinaten. Aufbewahrung nach der Standardeinstellung von Cloud Logging.
- **Benutzerkonten** (Firestore) sind nicht Teil dieses Konzepts.

## Soft Delete und Sicherungen

Google Cloud Storage hält gelöschte Objekte in neuen Buckets standardmäßig 7 Tage wiederherstellbar (Soft Delete). Damit wäre auch ein „unmittelbar gelöschtes“ Originalvideo noch 7 Tage vorhanden. Soft Delete wird deshalb abgeschaltet (Entscheidung vom 31.10.2026), die Versionierung muss aus sein:

```
gcloud storage buckets update gs://BUCKET_NAME --clear-soft-delete
gcloud storage buckets update gs://BUCKET_NAME --no-versioning
gcloud storage buckets describe gs://BUCKET_NAME --format="yaml(soft_delete_policy,versioning)"
```

Erwartet: keine `soft_delete_policy` mit Dauer größer 0, `versioning` nicht aktiv.

Firestore (Benutzer, Kontaktanfragen): Point-in-Time-Recovery und geplante Sicherungen prüfen. Sind sie an, bleiben gelöschte Kontaktanfragen bis zu 7 Tage (PITR) bzw. für die Aufbewahrung der Sicherung wiederherstellbar; das in der Datenschutzerklärung nennen oder abschalten:

```
gcloud firestore databases describe --format="yaml(pointInTimeRecoveryEnablement,locationId)"
gcloud firestore backups schedules list --database="(default)"
```

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
