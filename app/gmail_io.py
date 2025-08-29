import base64, email
from typing import Dict
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

def oauth_flow(client_json_path: str, redirect_uri: str):
    return Flow.from_client_secrets_file(client_json_path, scopes=SCOPES, redirect_uri=redirect_uri)

def creds_from_dict(d: Dict) -> Credentials:
    return Credentials(**d)

def gmail_service(creds_dict: Dict):
    creds = creds_from_dict(creds_dict)
    return build("gmail", "v1", credentials=creds)

def list_messages(svc, q='label:inbox newer_than:1d from:airbnb.com', max_results=10):
    res = svc.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    return res.get("messages", [])

def get_message(svc, msg_id):
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()

def extract_plain(payload):
    mt = payload.get("mimeType")
    if mt == "text/plain":
        data = payload.get("body", {}).get("data")
        if data: return base64.urlsafe_b64decode(data).decode("utf-8", "ignore")
    if mt and mt.startswith("multipart"):
        for p in payload.get("parts", []):
            if p.get("mimeType") == "text/plain":
                data = p.get("body", {}).get("data")
                if data: return base64.urlsafe_b64decode(data).decode("utf-8", "ignore")
    return ""

def send_reply(svc, to_addr: str, subject: str, body_text: str, thread_id: str | None = None):
    msg = email.message.EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = f"Re: {subject}"
    msg.set_content(body_text)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id
    return svc.users().messages().send(userId="me", body=payload).execute()
