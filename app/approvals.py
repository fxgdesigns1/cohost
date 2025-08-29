import os, hmac, hashlib, json, base64, time
from typing import Dict
from fastapi import HTTPException

SECRET = os.getenv("SECRET_KEY", "dev-secret")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

def _b64u(d: bytes) -> str:
    return base64.urlsafe_b64encode(d).decode().rstrip("=")

def _b64ud(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def make_token(payload: Dict, exp_seconds: int = 7*24*3600) -> str:
    data = {**payload, "exp": int(time.time()) + exp_seconds}
    body = _b64u(json.dumps(data, separators=(",",":")).encode())
    sig = _b64u(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"

def verify_token(token: str) -> Dict:
    try:
        body, sig = token.split(".", 1)
        expect = _b64u(hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expect):
            raise HTTPException(status_code=400, detail="bad_signature")
        data = json.loads(_b64ud(body))
        if int(time.time()) > int(data["exp"]):
            raise HTTPException(status_code=400, detail="token_expired")
        return data
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_token")

def approval_links(host_id: str, draft_id: str) -> Dict[str, str]:
    from urllib.parse import urlencode
    approve_tok = make_token({"a":"approve","h":host_id,"d":draft_id})
    edit_tok    = make_token({"a":"edit","h":host_id,"d":draft_id})
    reject_tok  = make_token({"a":"reject","h":host_id,"d":draft_id})
    return {
        "approve": f"{BASE_URL}/approve?{urlencode({'token': approve_tok})}",
        "edit":    f"{BASE_URL}/edit?{urlencode({'token': edit_tok})}",
        "reject":  f"{BASE_URL}/reject?{urlencode({'token': reject_tok})}"
    }
