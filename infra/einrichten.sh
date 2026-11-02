#!/usr/bin/env bash
# Einrichtung und erstes Deployment des Backends in einem Google-Cloud-Projekt
# (docs/BETRIEB.md). In der Cloud Shell im Ordner des Repos ausführen:
#
#   ADMIN_EMAIL=ihre@adresse.de bash infra/einrichten.sh
#
# Optional: PROJECT_ID (Projekt des Backends, Standard motavi-90305), BUCKET,
# WEBSITE, FIREBASE_PROVIDERS. Die Anmeldung läuft immer über das
# Firebase-Projekt motavi-90305, auch wenn das Backend in einem anderen Projekt liegt.
# Das Skript kann mehrfach laufen; vorhandene Teile werden übersprungen.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-motavi-90305}"
REGION="europe-west3"
BUCKET="${BUCKET:-}"
WEBSITE="${WEBSITE:-https://motavi.ai.studio}"
ADMIN_EMAIL="${ADMIN_EMAIL:?Bitte ADMIN_EMAIL=ihre@adresse.de voranstellen}"
FIREBASE_PROVIDERS="${FIREBASE_PROVIDERS:-password,google}"
# Web-Konfiguration aus der Firebase-Konsole (nicht geheim)
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-motavi-90305}"
FIREBASE_API_KEY="${FIREBASE_API_KEY:-AIzaSyDY83RpXYo0E3HnLTKNYGmf7MjsHUTiswM}"
FIREBASE_AUTH_DOMAIN="${FIREBASE_AUTH_DOMAIN:-${FIREBASE_PROJECT_ID}.firebaseapp.com}"
FIREBASE_APP_ID="${FIREBASE_APP_ID:-1:919373958459:web:d3d7d5655f60c33297fb1e}"

schritt() { printf '\n== %s\n' "$*"; }

gcloud config set project "$PROJECT_ID" >/dev/null
echo "Projekt des Backends: $PROJECT_ID, Anmeldung über Firebase-Projekt: $FIREBASE_PROJECT_ID"
NUMMER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
SA="motavi-backend@${PROJECT_ID}.iam.gserviceaccount.com"
URL="https://motavi-backend-${NUMMER}.${REGION}.run.app"

schritt "1/8 Dienste einschalten (Abrechnung muss im Projekt aktiv sein)"
# compute: Cloud Build nutzt in neuen Projekten dessen Standard-Dienstkonto
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com firestore.googleapis.com storage.googleapis.com iam.googleapis.com compute.googleapis.com

schritt "2/8 Ablage für Container-Images"
gcloud artifacts repositories describe motavi --location="$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create motavi --repository-format=docker --location="$REGION"

schritt "3/8 Bucket für Videos und Ergebnisse (Frankfurt, ohne Soft Delete und Versionierung)"
# vorhandenen Bucket aus einer früheren Einrichtung übernehmen
if [[ -z "$BUCKET" ]] && gcloud secrets describe GCS_BUCKET_NAME >/dev/null 2>&1; then
  BUCKET="$(gcloud secrets versions access latest --secret=GCS_BUCKET_NAME)"
fi
BUCKET="${BUCKET:-${PROJECT_ID}-videos}"
echo "Bucket: $BUCKET (die Lifecycle-Regeln löschen dort auch alte Originalvideos, docs/LOESCHKONZEPT.md)"
gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 \
  || gcloud storage buckets create "gs://${BUCKET}" --location="$REGION" --uniform-bucket-level-access
gcloud storage buckets update "gs://${BUCKET}" --clear-soft-delete --no-versioning --lifecycle-file=infra/gcs_lifecycle.json
CORS="$(mktemp)"
sed "s#https://APP_DOMAIN#${URL}#" infra/gcs_cors.json > "$CORS"
gcloud storage buckets update "gs://${BUCKET}" --cors-file="$CORS"

schritt "4/8 Firestore (Benutzer, Zugänge, Kontaktanfragen)"
if ! gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  gcloud firestore databases create --location="$REGION" --type=firestore-native
fi
gcloud firestore databases describe --database='(default)' --format='value(locationId)' | sed 's/^/Region der Datenbank: /'
gcloud firestore fields ttls update loeschen_am --collection-group=kontaktanfragen --enable-ttl --async >/dev/null 2>&1 \
  || echo "TTL-Regel für Kontaktanfragen besteht schon oder wird gerade angelegt."

schritt "5/8 Dienstkonto des Backends und seine Rechte"
gcloud iam service-accounts describe "$SA" >/dev/null 2>&1 \
  || gcloud iam service-accounts create motavi-backend --display-name="Motavi Backend"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" --member="serviceAccount:${SA}" --role=roles/storage.objectUser >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role=roles/datastore.user --condition=None >/dev/null

schritt "6/8 Secrets"
gcloud secrets describe JWT_SECRET >/dev/null 2>&1 \
  || openssl rand -base64 48 | tr -d '\n' | gcloud secrets create JWT_SECRET --data-file=- --replication-policy=user-managed --locations="$REGION"
gcloud secrets describe GCS_BUCKET_NAME >/dev/null 2>&1 \
  || printf '%s' "$BUCKET" | gcloud secrets create GCS_BUCKET_NAME --data-file=- --replication-policy=user-managed --locations="$REGION"
for s in JWT_SECRET GCS_BUCKET_NAME; do
  gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:${SA}" --role=roles/secretmanager.secretAccessor >/dev/null
done

schritt "7/8 Rechte für Cloud Build (bauen und auf Cloud Run veröffentlichen)"
for BAU in "${NUMMER}-compute@developer.gserviceaccount.com" "${NUMMER}@cloudbuild.gserviceaccount.com"; do
  gcloud iam service-accounts describe "$BAU" >/dev/null 2>&1 || [[ "$BAU" == *cloudbuild* ]] || continue
  for ROLLE in roles/cloudbuild.builds.builder roles/run.admin; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${BAU}" --role="$ROLLE" --condition=None >/dev/null 2>&1 || true
  done
  gcloud iam service-accounts add-iam-policy-binding "$SA" --member="serviceAccount:${BAU}" --role=roles/iam.serviceAccountUser >/dev/null 2>&1 || true
done

schritt "8/8 Bauen und veröffentlichen (dauert etwa 10 bis 15 Minuten)"
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions="^;^_PUBLIC_APP_URL=${URL};_CORS_ORIGINS=${WEBSITE};_FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID};_FIREBASE_API_KEY=${FIREBASE_API_KEY};_FIREBASE_AUTH_DOMAIN=${FIREBASE_AUTH_DOMAIN};_FIREBASE_APP_ID=${FIREBASE_APP_ID};_FIREBASE_PROVIDERS=${FIREBASE_PROVIDERS};_ADMIN_EMAILS=${ADMIN_EMAIL}" \
  .

ECHT="$(gcloud run services describe motavi-backend --region="$REGION" --format='value(status.url)')"
if [[ "$ECHT" != "$URL" ]]; then
  echo "Adresse des Dienstes weicht ab, PUBLIC_APP_URL wird angepasst: $ECHT"
  gcloud run services update motavi-backend --region="$REGION" --update-env-vars="PUBLIC_APP_URL=${ECHT}" >/dev/null
  URL="$ECHT"
fi

cat <<FERTIG

Fertig. Adresse des Werkzeugs: ${URL}

Noch von Hand in der Firebase-Konsole (Projekt ${FIREBASE_PROJECT_ID}):
  1. Authentication > Sign-in method: Anbieter aktivieren (${FIREBASE_PROVIDERS}).
  2. Authentication > Settings > Authorized domains: ${URL#https://} hinzufügen.
Danach unter ${URL}/login mit ${ADMIN_EMAIL} anmelden.
FERTIG
