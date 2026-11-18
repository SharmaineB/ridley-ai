import json
import re

from .config import settings
from .rag import expand

INTENTS = [
    "account_unlock", "password_reset", "mfa_no_prompt", "vpn_issue", "wfh_internet", "softphone_audio",
    "call_drops", "citrix_slow", "access_request", "headset_issue", "device_lost", "phishing_report",
    "human_request", "kb_question", "out_of_scope",
]

CATEGORY = {
    "account_unlock": "Accounts", "password_reset": "Accounts", "mfa_no_prompt": "Accounts",
    "vpn_issue": "VPN / WFH", "wfh_internet": "VPN / WFH", "softphone_audio": "Telephony",
    "call_drops": "Telephony", "citrix_slow": "Citrix / VDI", "access_request": "Access",
    "headset_issue": "Hardware", "device_lost": "Hardware", "phishing_report": "Security",
    "human_request": "General", "kb_question": "General", "out_of_scope": "General",
}

RULES = [
    ("device_lost", r"stolen|ninakaw|nanakaw|nawala|lost (my |the )?(laptop|device|computer|phone)|(laptop|device).{0,20}(lost|stolen)"),
    ("phishing_report", r"phish|suspicious (email|link|message)|email (asking|asks) for my password"),
    ("human_request", r"\b(human|real person|technician|live agent|talk to (a |an )?(person|someone|agent))\b"),
    ("access_request", r"(need|request|want|get|give me|kailangan).{0,20}access|access (to|for)|permission to"),
    ("mfa_no_prompt", r"(mfa|otp|authenticator|verification code|2fa).{0,40}(not|no|walang|di)|(not|no|walang).{0,30}(mfa|otp|authenticator|prompt)"),
    ("account_unlock", r"na-? ?lock|naka-? ?lock|locked|lockout|lock(ed)? out|can'?t (log ?in|sign in)|cannot (log ?in|sign in)|di (ako )?maka-?log ?in|failed (login|attempts)"),
    ("password_reset", r"password.{0,30}(reset|forgot|expired|change|nakalimutan)|(reset|forgot|nakalimutan).{0,30}password|forgot my pass"),
    ("vpn_issue", r"\bvpn\b"),
    ("citrix_slow", r"citrix|\bvdi\b|virtual desktop"),
    ("call_drops", r"call.{0,15}(drop|putol|cut)|drop(ping)? call|naputol"),
    ("softphone_audio", r"softphone|no sound|one-?way|(audio|tunog|sound).{0,30}(not|walang|no|issue|problem)|can'?t hear|cannot hear|di (ko )?marinig"),
    ("headset_issue", r"headset|\bmic\b|microphone"),
    ("wfh_internet", r"\bwfh\b|work(ing)? from home|internet|wi-?fi|bandwidth"),
]


def rule_intent(text: str):
    low = text.lower()
    for intent, pattern in RULES:
        if re.search(pattern, low):
            return intent, 0.9
    return "kb_question", 0.5


def classify_intent(text: str):
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            res = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": (
                        "You classify IT helpdesk messages from call center agents. The text may be English, Tagalog or a mix. "
                        f"Return JSON with keys intent and confidence (0 to 1). intent must be one of: {', '.join(INTENTS)}. "
                        "Use out_of_scope for anything that is not an IT support request.")},
                    {"role": "user", "content": text},
                ],
            )
            data = json.loads(res.choices[0].message.content)
            if data.get("intent") in INTENTS:
                return data["intent"], float(data.get("confidence", 0.7))
        except Exception:
            pass
    return rule_intent(text)


def build_answer(question: str, chunks: list, first_name: str):
    if settings.openai_api_key and chunks:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            context = "\n\n".join(f"[{c['kb_id']}] {c['title']} - {c['section']}\n{c['content']}" for c in chunks)
            res = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": (
                        "You are Ridley, the IT support assistant for TaskUs call center agents. Answer only from the context. "
                        "If the context does not contain the answer, say you will connect the agent to a technician. "
                        "Reply in the language the agent used, keep it short, use numbered steps when the SOP has steps, "
                        "and never invent gateway names, numbers or policies.")},
                    {"role": "user", "content": f"Context:\n{context}\n\nAgent ({first_name}) asks: {question}"},
                ],
            )
            return res.choices[0].message.content.strip()
        except Exception:
            pass
    return extractive_answer(chunks)


def extractive_answer(chunks: list):
    if not chunks:
        return ""
    best = chunks[0]
    parts = [best["content"]]
    for c in chunks[1:]:
        if c["kb_id"] == best["kb_id"] and c["content"] not in parts:
            parts.append(c["content"])
            break
    text = "\n\n".join(parts).strip()
    if len(text) > 900:
        text = text[:900].rsplit(" ", 1)[0] + "..."
    return text


def keywords_for(text: str):
    return sorted(set(expand(text)))[:12]
