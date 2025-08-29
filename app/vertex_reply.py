import os
from google.cloud import aiplatform

PROJECT = os.getenv("GCP_PROJECT_ID")
LOCATION = os.getenv("GCP_LOCATION", "europe-west2")
MODEL = os.getenv("MODEL", "gemini-1.5-pro")

_client_inited = False
def _init():
    global _client_inited
    if not _client_inited:
        aiplatform.init(project=PROJECT, location=LOCATION)
        _client_inited = True

SYSTEM_PROMPT_BASE = """You are an AI co-host for Airbnb. Always be concise, friendly, and professional.
Never commit to refunds, discounts, or rule exceptions. If asked about them, recommend escalation to the host.
Use British English and local time. If you don't know, ask a brief clarifying question."""

def build_system_prompt(listing_cfg: dict):
    parts = [SYSTEM_PROMPT_BASE]
    parts.append(f"Check-in after: {listing_cfg.get('check_in_after')}")
    parts.append(f"Check-out before: {listing_cfg.get('check_out_before')}")
    parts.append(f"Wi-Fi: SSID {listing_cfg.get('wifi_ssid')}, Password {listing_cfg.get('wifi_password')}")
    parts.append(f"Parking: {listing_cfg.get('parking_notes')}")
    return "\n".join(parts)

def llm_reply(message_text: str, listing_cfg: dict, guest_name="there") -> str:
    _init()
    from vertexai.generative_models import GenerativeModel, GenerationConfig, SafetySetting, HarmCategory

    sys_prompt = build_system_prompt(listing_cfg)
    model = GenerativeModel(MODEL, system_instruction=sys_prompt)
    config = GenerationConfig(max_output_tokens=256, temperature=0.4)
    safety = [
        SafetySetting(HarmCategory.HARM_CATEGORY_HATE_SPEECH, SafetySetting.BlockThreshold.BLOCK_NONE),
        SafetySetting(HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, SafetySetting.BlockThreshold.BLOCK_NONE),
        SafetySetting(HarmCategory.HARM_CATEGORY_HARASSMENT, SafetySetting.BlockThreshold.BLOCK_NONE),
        SafetySetting(HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, SafetySetting.BlockThreshold.BLOCK_NONE),
    ]
    prompt = f"Guest ({guest_name}) asked:\n{message_text}\n\nReply in 1–4 concise sentences."
    out = model.generate_content([prompt], generation_config=config, safety_settings=safety)
    return out.text.strip() if hasattr(out, "text") else ""
