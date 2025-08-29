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

def save_gmail_creds(host_id: str, creds: Dict):
    db_client = db()
    if db_client is None:
        print(f"Mock: save_gmail_creds({host_id})")
        return
    db_client.collection("tenants").document(host_id)\
      .collection("oauth").document("gmail").set(creds, merge=True)

def load_gmail_creds(host_id: str) -> Optional[Dict]:
    db_client = db()
    if db_client is None:
        print(f"Mock: load_gmail_creds({host_id})")
        return None
    snap = db_client.collection("tenants").document(host_id)\
              .collection("oauth").document("gmail").get()
    return snap.to_dict() if snap.exists else None
