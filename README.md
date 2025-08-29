# AI Co‑Host (Vertex + Gmail + Cloud Run)
**Multi-tenant Airbnb co-host prototype** using Gmail relays, Vertex AI (Gemini), Firestore, Cloud Run, and a one‑click approval flow.

## Quick Start (Local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```
- Visit `http://localhost:8000/docs` for endpoints.
- Onboard a host: `POST /tenants/register`, then open `/oauth2/google?hostId=...`.
- Trigger polling: `POST /poll` (creates drafts + sends approval email to host).

## Deploy (GitHub Actions → Cloud Run)
1) Create Artifact Registry (first time):
```bash
gcloud artifacts repositories create cohost --repository-format=docker --location=europe-west2
```
2) Add GitHub Secrets:
   - `GCP_PROJECT_ID` = your GCP project id
   - `GCP_SA_KEY` = contents of a service account key (JSON) with roles:
     - run.admin, iam.serviceAccountUser, secretmanager.secretAccessor, aiplatform.user, datastore.user
3) Push to `main` → build & deploy.

## Cloud Run config
After first deploy, set env and secrets:
```bash
gcloud run services update cohost-api --region=europe-west2   --set-env-vars BASE_URL=https://<cloud-run-url>,SECRET_KEY=<long-random>,APPROVE_MODE=false

# Store OAuth secrets in Secret Manager, then mount:
gcloud run services update cohost-api --region=europe-west2   --update-secrets OAUTH_CLIENT_ID=OAUTH_CLIENT_ID:latest,OAUTH_CLIENT_SECRET=OAUTH_CLIENT_SECRET:latest,OAUTH_REDIRECT_URI=OAUTH_REDIRECT_URI:latest
```

## Automate polling (Cloud Scheduler → /poll)
- Public: send an X-API-Key header (add simple check in /poll).
- Private: use OIDC with a scheduler service account.

---
Generated on 2025-08-29.
