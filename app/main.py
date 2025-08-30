import os
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from pydantic_settings import BaseSettings
from app.gmail_io import oauth_flow, gmail_service, send_reply
from app.tenants import upsert_tenant, set_active, get_tenant, list_active_hosts, save_listing_config, get_listing_config
from app.token_store import save_gmail_creds, load_gmail_creds
from app.poller import process_host
from app.approvals import verify_token
from app.datastore import get_draft, set_draft_status, delete_draft, log_message, upsert_thread_marker

class Settings(BaseSettings):
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/oauth2/callback/google"
    OAUTH_CLIENT_ID: str = ""
    OAUTH_CLIENT_SECRET: str = ""
    BASE_URL: str = "http://localhost:8000"
    SECRET_KEY: str = "local-dev-super-random-string"
    APPROVE_MODE: bool = False
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "europe-west2"
    MODEL: str = "gemini-1.5-pro"
    
    class Config: 
        env_file = ".env"
        extra = "ignore"

settings = Settings()
app = FastAPI(title="AI Cohost (Multi-tenant)")

@app.get("/")
def health():
    return {"status": "ok"}

# ---------- Tenant onboarding ----------
@app.post("/tenants/register")
def tenant_register(hostId: str, hostEmail: str):
    upsert_tenant(hostId, hostEmail)
    return {"ok": True, "hostId": hostId}

@app.post("/tenants/{hostId}/listings/{listingId}")
def tenant_listing(hostId: str, listingId: str, cfg: dict):
    save_listing_config(hostId, listingId, cfg)
    return {"ok": True}

@app.get("/tenants/{hostId}/listings/{listingId}")
def get_listing(hostId: str, listingId: str):
    return {"ok": True, "config": get_listing_config(hostId, listingId)}

# ---------- OAuth (per host) ----------
@app.get("/oauth2/google")
def oauth_start(hostId: str):
    if not get_tenant(hostId):
        raise HTTPException(status_code=400, detail="Unknown hostId. Call /tenants/register first.")
    from app.gmail_io import oauth_flow
    flow = oauth_flow("client_secret.json", settings.OAUTH_REDIRECT_URI)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=f"host:{hostId}"
    )
    return RedirectResponse(auth_url)

@app.get("/oauth2/callback/google")
def oauth_callback(request: Request):
    state = request.query_params.get("state") or ""
    code = request.query_params.get("code")
    if not state.startswith("host:") or not code:
        return JSONResponse({"ok": False, "error": "bad_state_or_code"}, status_code=400)
    host_id = state.split("host:", 1)[1]
    if not get_tenant(host_id):
        return JSONResponse({"ok": False, "error": "unknown_host"}, status_code=400)

    from app.gmail_io import oauth_flow
    flow = oauth_flow("client_secret.json", settings.OAUTH_REDIRECT_URI)
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_gmail_creds(host_id, {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    })
    set_active(host_id, True)
    return {"ok": True, "hostId": host_id}

# ---------- Poll all active tenants ----------
@app.post("/poll")
def poll_all():
    results = []
    for host_id in list_active_hosts():
        results.append(process_host(host_id, approve_mode=settings.APPROVE_MODE))
    return {"ok": True, "results": results}

# ---------- Approval routes ----------
@app.get("/approve", response_class=HTMLResponse)
def approve(token: str):
    data = verify_token(token)
    if data.get("a") != "approve":
        return HTMLResponse("<h3>Invalid action.</h3>", status_code=400)
    host_id, draft_id = data["h"], data["d"]
    d = get_draft(host_id, draft_id)
    if not d:
        return HTMLResponse("<h3>Draft not found.</h3>", status_code=404)
    creds = load_gmail_creds(host_id)
    if not creds:
        return HTMLResponse("<h3>Host not connected.</h3>", status_code=400)
    svc = gmail_service(creds)
    send_reply(svc, d["to_addr"], d["subject"], d["body"], d["thread_id"])
    log_message(host_id, d["thread_id"], "outbound", d["body"], {"approved": True})
    upsert_thread_marker(host_id, d["thread_id"], draft_id)
    set_draft_status(host_id, draft_id, "sent")
    delete_draft(host_id, draft_id)
    return HTMLResponse("<h3>✅ Sent to guest.</h3>")

@app.get("/edit", response_class=HTMLResponse)
def edit(token: str):
    data = verify_token(token)
    if data.get("a") != "edit":
        return HTMLResponse("<h3>Invalid action.</h3>", status_code=400)
    host_id, draft_id = data["h"], data["d"]
    d = get_draft(host_id, draft_id)
    if not d:
        return HTMLResponse("<h3>Draft not found.</h3>", status_code=404)
    html = f'''
    <html><body style="font-family: system-ui; max-width:700px; margin:2rem auto;">
      <h2>Edit & Send</h2>
      <p><b>Subject:</b> {d['subject']}</p>
      <form method="POST" action="/edit/send">
        <input type="hidden" name="token" value="{token}">
        <textarea name="body" rows="10" style="width:100%;">{d['body']}</textarea>
        <div style="margin-top:1rem;">
          <button type="submit">Send</button>
        </div>
      </form>
      <p style="margin-top:1rem;"><a href="/reject?token={token}">Reject</a></p>
    </body></html>
    '''
    return HTMLResponse(html)

@app.post("/edit/send", response_class=HTMLResponse)
def edit_send(token: str = Form(...), body: str = Form(...)):
    data = verify_token(token)
    if data.get("a") not in ("edit","approve"):
        return HTMLResponse("<h3>Invalid action.</h3>", status_code=400)
    host_id, draft_id = data["h"], data["d"]
    d = get_draft(host_id, draft_id)
    if not d:
        return HTMLResponse("<h3>Draft not found.</h3>", status_code=404)
    creds = load_gmail_creds(host_id)
    if not creds:
        return HTMLResponse("<h3>Host not connected.</h3>", status_code=400)
    svc = gmail_service(creds)
    send_reply(svc, d["to_addr"], d["subject"], body, d["thread_id"])
    log_message(host_id, d["thread_id"], "outbound", body, {"approved": True, "edited": True})
    upsert_thread_marker(host_id, d["thread_id"], draft_id)
    set_draft_status(host_id, draft_id, "sent")
    delete_draft(host_id, draft_id)
    return HTMLResponse("<h3>✅ Edited reply sent to guest.</h3>")

@app.get("/reject", response_class=HTMLResponse)
def reject(token: str):
    data = verify_token(token)
    if data.get("a") != "reject":
        return HTMLResponse("<h3>Invalid action.</h3>", status_code=400)
    host_id, draft_id = data["h"], data["d"]
    from app.datastore import get_draft, delete_draft, set_draft_status
    if get_draft(host_id, draft_id):
        set_draft_status(host_id, draft_id, "rejected")
        delete_draft(host_id, draft_id)
    return HTMLResponse("<h3>🛑 Draft rejected. No message sent.</h3>")

@app.get("/healthz")
def health():
    return {"ok": True}
