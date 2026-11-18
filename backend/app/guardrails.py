import re

CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?63|0)[ -]?9\d{2}[ -]?\d{3}[ -]?\d{4}(?!\d)")
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
GOV_ID = re.compile(r"\b\d{2}-\d{7}-\d\b|\b\d{3}-\d{3}-\d{3}(?:-\d{3})?\b")
SECRET = re.compile(r"(?i)\b(password|passcode|pin|pwd)\b(\s*(?:is|:|=)\s*)(\S+)")

INJECTION = [
    r"ignore (all |any |the |your |previous |prior |above )+(instructions|rules|prompts?)",
    r"disregard (all |any |the |your |previous )*(instructions|rules|guidelines)",
    r"(reveal|show|print|repeat|tell me) (me )?(your|the) (system )?(prompt|instructions)",
    r"system prompt",
    r"you are now\b",
    r"developer mode",
    r"jailbreak",
    r"forget (everything|your (rules|instructions))",
    r"pretend (to be|you are)",
    r"bypass (the )?(otp|verification|guardrail|security|filter)",
    r"override (the )?(rules|security|policy|role)",
    r"act as (an? )?(admin|administrator|root|developer)",
]
INJECTION_RE = [re.compile(p, re.I) for p in INJECTION]

EMP_ID = re.compile(r"\bNX-\d{5}\b", re.I)


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def redact_pii(text: str):
    findings = []

    def card_sub(m):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits):
            findings.append(("PII redacted", "Card number redacted"))
            return "[CARD REDACTED]"
        return m.group(0)

    out = CARD.sub(card_sub, text)

    def phone_sub(m):
        findings.append(("PII redacted", "Phone number redacted"))
        return "[PHONE REDACTED]"

    out = PHONE.sub(phone_sub, out)

    def email_sub(m):
        findings.append(("PII redacted", "Email address redacted"))
        return "[EMAIL REDACTED]"

    out = EMAIL.sub(email_sub, out)

    def id_sub(m):
        findings.append(("PII redacted", "Government ID redacted"))
        return "[ID REDACTED]"

    out = GOV_ID.sub(id_sub, out)

    def secret_sub(m):
        findings.append(("PII redacted", "Password or PIN redacted"))
        return f"{m.group(1)}{m.group(2)}[SECRET REDACTED]"

    out = SECRET.sub(secret_sub, out)
    return out, findings


def detect_injection(text: str) -> bool:
    return any(p.search(text) for p in INJECTION_RE)


def other_employee_ids(text: str, own_id: str):
    return [m.upper() for m in EMP_ID.findall(text) if m.upper() != own_id.upper()]
