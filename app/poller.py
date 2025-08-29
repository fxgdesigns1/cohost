from typing import Dict
from app.gmail_io import gmail_service, list_messages, get_message, extract_plain, send_reply
from app.router import propose_template
from app.vertex_reply import llm_reply
from app.datastore import log_message, upsert_thread_marker, last_processed_id, create_draft
from app.tenants import get_listing_config, get_tenant
from app.token_store import load_gmail_creds
from app.approvals import approval_links

def _send_host_approval_email(svc, host_email: str, subject: str, preview: str, links: Dict[str,str]):
    body = (
        "Approval needed for a guest reply.\n\n"
        f"Subject: {subject}\n\n"
        "Draft reply:\n"
        "--------------------------------\n"
        f"{preview}\n"
        "--------------------------------\n\n"
        f"Approve: {links['approve']}\n"
        f"Edit & Send: {links['edit']}\n"
        f"Reject: {links['reject']}\n\n"
        "— AI Co-Host"
    )
    return send_reply(svc, host_email, f"[Approve] {subject}", body_text=body, thread_id=None)

def process_host(host_id: str, approve_mode: bool = False) -> Dict:
    creds = load_gmail_creds(host_id)
    if not creds:
        return {"hostId": host_id, "skipped": "no_creds"}

    tenant = get_tenant(host_id) or {}
    host_email = tenant.get("hostEmail")
    svc = gmail_service(creds)
    msgs = list_messages(svc)
    handled, drafted = 0, 0

    for m in msgs:
        full = get_message(svc, m["id"])
        headers = {h["name"].lower(): h["value"] for h in full["payload"]["headers"]}
        subject = headers.get("subject","")
        to_addr = headers.get("reply-to") or headers.get("from")
        thread_id = full.get("threadId", m["id"])
        msg_id = full.get("id")

        if last_processed_id(host_id, thread_id) == msg_id:
            continue

        body = extract_plain(full["payload"])
        log_message(host_id, thread_id, "inbound", body, {"subject": subject})

        listing_cfg = get_listing_config(host_id)
        text, auto_ok, _ = propose_template(body, "there")
        source = "template"
        if not text:
            text = llm_reply(body, listing_cfg, "there")
            auto_ok, source = False, "llm"

        if approve_mode and auto_ok:
            send_reply(svc, to_addr, subject, text, thread_id)
            log_message(host_id, thread_id, "outbound", text, {"auto_sent": True, "source": source})
            handled += 1
        else:
            draft_id = msg_id
            create_draft(host_id, draft_id, {
                "thread_id": thread_id,
                "to_addr": to_addr,
                "subject": subject,
                "body": text,
                "source": source,
                "auto_ok": auto_ok
            })
            if host_email:
                links = approval_links(host_id, draft_id)
                _send_host_approval_email(svc, host_email, subject, text, links)
            log_message(host_id, thread_id, "draft", text, {"auto_sent": False, "source": source})
            drafted += 1

        upsert_thread_marker(host_id, thread_id, msg_id)

    return {"hostId": host_id, "handled": handled, "drafted": drafted}
