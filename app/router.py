import re
from typing import Tuple

SAFE_RULES = [
    (re.compile(r'\bcheck[\s-]?in|arrival|access\b', re.I),
     "Check-in is after 3pm. Smart-lock code arrives at 9am on arrival day."),
    (re.compile(r'\bcheck[\s-]?out|departure\b', re.I),
     "Check-out is 11am. Need extra time? I’ll check availability."),
    (re.compile(r'\bwi[-\s]?fi|internet\b', re.I),
     "Wi-Fi: Network “Home-Guest”, Password “StayHappy2025”."),
    (re.compile(r'\bparking|car park\b', re.I),
     "Free on-street after 6pm; nearest paid car park is 2 min away on King St.")
]

SENSITIVE_RX = re.compile(
    r'\b(refund|discount|compensat|damage|exception|special offer|price match)\b',
    re.I
)

def propose_template(text: str, guest_name: str = "there") -> Tuple[str, bool, float]:
    m = text or ""
    for rx, templ in SAFE_RULES:
        if rx.search(m):
            return f"Hi {guest_name}! {templ}", True, 0.95
    if SENSITIVE_RX.search(m):
        return "Thanks for reaching out! I’ve flagged this for a quick review and will get back shortly.", False, 0.8
    return "", False, 0.0  # empty → let LLM handle
