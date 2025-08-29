import datetime as dt
from typing import Optional, Dict
from google.cloud import firestore

_db = None
def db():
    global _db
    if _db is None:
        try:
            _db = firestore.Client()
        except Exception as e:
            print(f"Warning: Firestore not available: {e}")
            return None
    return _db

def log_message(host_id: str, thread_id: str, direction: str, body: str, meta: dict):
    db_client = db()
    if db_client is None:
        print(f"Mock: log_message({host_id}, {thread_id}, {direction})")
        return
    doc = {
        "thread_id": thread_id,
        "direction": direction,  # inbound/outbound/draft
        "body": body[:8000],
        "meta": meta or {},
        "ts": dt.datetime.utcnow()
    }
    db_client.collection("tenants").document(host_id)\
      .collection("messages").add(doc)

def upsert_thread_marker(host_id: str, thread_id: str, last_msg_id: str):
    db_client = db()
    if db_client is None:
        print(f"Mock: upsert_thread_marker({host_id}, {thread_id}, {last_msg_id})")
        return
    db_client.collection("tenants").document(host_id)\
      .collection("threads").document(thread_id).set({
        "lastMessageId": last_msg_id,
        "updatedAt": dt.datetime.utcnow()
      }, merge=True)

def last_processed_id(host_id: str, thread_id: str) -> str | None:
    db_client = db()
    if db_client is None:
        print(f"Mock: last_processed_id({host_id}, {thread_id})")
        return None
    snap = db_client.collection("tenants").document(host_id)\
             .collection("threads").document(thread_id).get()
    if snap.exists:
        return snap.to_dict().get("lastMessageId")
    return None

# Drafts
def create_draft(host_id: str, draft_id: str, data: Dict):
    db_client = db()
    if db_client is None:
        print(f"Mock: create_draft({host_id}, {draft_id})")
        return
    data = {**data, "status": "pending", "createdAt": dt.datetime.utcnow()}
    db_client.collection("tenants").document(host_id)\
      .collection("drafts").document(draft_id).set(data, merge=False)

def get_draft(host_id: str, draft_id: str) -> Optional[Dict]:
    db_client = db()
    if db_client is None:
        print(f"Mock: get_draft({host_id}, {draft_id})")
        return None
    snap = db_client.collection("tenants").document(host_id)\
             .collection("drafts").document(draft_id).get()
    return snap.to_dict() if snap.exists else None

def set_draft_status(host_id: str, draft_id: str, status: str):
    db_client = db()
    if db_client is None:
        print(f"Mock: set_draft_status({host_id}, {draft_id}, {status})")
        return
    db_client.collection("tenants").document(host_id)\
      .collection("drafts").document(draft_id).set({"status": status}, merge=True)

def delete_draft(host_id: str, draft_id: str):
    db_client = db()
    if db_client is None:
        print(f"Mock: delete_draft({host_id}, {draft_id})")
        return
    db_client.collection("tenants").document(host_id)\
      .collection("drafts").document(draft_id).delete()
