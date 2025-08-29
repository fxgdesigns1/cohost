import datetime as dt
from typing import Dict, List, Optional
from google.cloud import firestore

_db = None
def db():
    global _db
    if _db is None:
        try:
            _db = firestore.Client()
        except Exception as e:
            print(f"Warning: Firestore not available: {e}")
            # Return a mock client for local development
            return None
    return _db

def upsert_tenant(host_id: str, email: str):
    db_client = db()
    if db_client is None:
        print(f"Mock: upsert_tenant({host_id}, {email})")
        return
    doc = db_client.collection("tenants").document(host_id)
    doc.set({
        "hostEmail": email,
        "active": False,
        "createdAt": dt.datetime.utcnow()
    }, merge=True)

def set_active(host_id: str, active: bool):
    db_client = db()
    if db_client is None:
        print(f"Mock: set_active({host_id}, {active})")
        return
    db_client.collection("tenants").document(host_id).set({"active": active}, merge=True)

def get_tenant(host_id: str) -> Optional[Dict]:
    db_client = db()
    if db_client is None:
        print(f"Mock: get_tenant({host_id})")
        return {"hostEmail": "test@example.com", "active": True}
    snap = db_client.collection("tenants").document(host_id).get()
    return snap.to_dict() if snap.exists else None

def list_active_hosts(limit: int = 200) -> List[str]:
    db_client = db()
    if db_client is None:
        print(f"Mock: list_active_hosts()")
        return ["host-you"]
    q = db_client.collection("tenants").where("active", "==", True).limit(limit)
    return [d.id for d in q.stream()]

def save_listing_config(host_id: str, listing_id: str, cfg: Dict):
    db_client = db()
    if db_client is None:
        print(f"Mock: save_listing_config({host_id}, {listing_id})")
        return
    db_client.collection("tenants").document(host_id)\
      .collection("listings").document(listing_id).set(cfg, merge=True)

def get_listing_config(host_id: str, listing_id: str = "default") -> Dict:
    db_client = db()
    if db_client is None:
        print(f"Mock: get_listing_config({host_id}, {listing_id})")
        return {
            "check_in_after": "15:00",
            "check_out_before": "11:00",
            "wifi_ssid": "Home-Guest",
            "wifi_password": "StayHappy2025",
            "parking_notes": "Free on-street after 18:00; nearest paid car park on King St.",
            "tone": "friendly, concise, professional",
            "blocked_auto_send_keywords": [
                "refund","discount","damage","compensation","price match","exception"
            ]
        }
    snap = db_client.collection("tenants").document(host_id)\
             .collection("listings").document(listing_id).get()
    if snap.exists:
        return snap.to_dict()
    return {
        "check_in_after": "15:00",
        "check_out_before": "11:00",
        "wifi_ssid": "Home-Guest",
        "wifi_password": "StayHappy2025",
        "parking_notes": "Free on-street after 18:00; nearest paid car park on King St.",
        "tone": "friendly, concise, professional",
        "blocked_auto_send_keywords": [
            "refund","discount","damage","compensation","price match","exception"
        ]
    }
