import re
import time
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from . import rag
from .config import settings
from .guardrails import detect_injection, other_employee_ids, redact_pii
from .llm import CATEGORY, build_answer, classify_intent
from .models import Conversation, Employee, Escalation, Incident, KBArticle, Message
from .services import (GROUP, PRIORITY, call_webhook, check_otp, create_ticket, issue_otp, log_function,
                       log_guardrail, run_function)
from .summary import build_summary

RESET_WORDS = re.compile(r"reset|unlock|password|pass\b|i-?lock|palitan|change", re.I)


def text_block(text, sources=None, actions=None):
    return {"type": "text", "text": text, "sources": sources or [], "actions": actions or []}


def save(db: Session, conv: Conversation, sender: str, text: str, blocks=None, latency=None, kb=None):
    m = Message(conversation_id=conv.conversation_id, sender=sender, content_redacted=text, blocks=blocks,
                latency_ms=latency, kb_article_id=kb, created_at=datetime.utcnow())
    db.add(m)
    db.flush()
    return m


def source_list(db: Session, chunks):
    seen, out = set(), []
    for c in chunks:
        if c["kb_id"] in seen:
            continue
        seen.add(c["kb_id"])
        out.append({"kb_id": c["kb_id"], "title": c["title"]})
    return out


def article_sources(db: Session, ids):
    rows = db.query(KBArticle).filter(KBArticle.kb_id.in_(ids), KBArticle.status == "active").all()
    seen = {}
    for r in rows:
        seen[r.kb_id] = {"kb_id": r.kb_id, "title": r.title}
    return [seen[i] for i in ids if i in seen]


def new_conversation(db: Session, emp: Employee) -> Conversation:
    conv = Conversation(conversation_id=uuid.uuid4().hex[:16], employee_id=emp.employee_id, state={})
    db.add(conv)
    db.flush()
    return conv


def active_incident(db: Session):
    return db.query(Incident).filter(Incident.active.is_(True)).first()


def escalate(db: Session, emp: Employee, conv: Conversation, intent: str, reason: str, chunks=None, steps=None,
             first_message=""):
    priority = "P1" if intent == "device_lost" else PRIORITY.get(intent, "P3")
    category = CATEGORY.get(intent, "General")
    group = {"device_lost": "Information Security", "phishing_report": "Information Security"}.get(intent, GROUP.get(category, "L1 Service Desk"))
    ref = f"ITSD-{uuid.uuid4().int % 9000 + 1000}"
    labels = {
        "device_lost": "Laptop stolen", "phishing_report": "Phishing email reported", "human_request": "Needs a technician",
    }
    summary_text = labels.get(intent) or (first_message[:80] or "Needs a technician")
    t = create_ticket(db, emp, summary_text, category, priority, group, "Escalated", None, ref)
    wh = call_webhook("create_incident_ticket", {"ticket_id": t.ticket_id, "priority": priority, "group": group})
    log_function(db, emp.employee_id, conv.conversation_id, "create_incident_ticket",
                 {"priority": priority, "group": group}, f"Success ({wh})")
    summary = build_summary(emp, intent, first_message or summary_text, chunks or [], reason, steps or [], priority)
    summary["suggested_reply"] = summary["suggested_reply"].replace("your ticket", t.ticket_id)
    esc = Escalation(conversation_id=conv.conversation_id, ticket_id=t.ticket_id, status="Waiting",
                     summary=summary, external_ref=ref)
    db.add(esc)
    conv.ticket_id = t.ticket_id
    conv.human_active = True
    conv.route = "Escalate"
    conv.state = {}
    db.flush()
    return t, esc


def escalation_reply(intent: str, ticket_id: str, priority: str, first: str):
    if intent == "device_lost":
        return (f"I'm sorry that happened. I hope you're okay. I've created priority ticket {ticket_id} and alerted Security, "
                "who will lock and wipe the laptop remotely. Please tell your team lead and get a police report within 48 hours.")
    if intent == "phishing_report":
        return (f"Thank you for reporting it. Please do not click anything in that email. I've sent it to Information Security under {ticket_id}. "
                "If you already clicked a link or typed your password, say so here and a technician will secure your account first.")
    return ("This needs a person from our team, so I'm connecting you to a technician now. "
            f"They'll have everything we've covered under {ticket_id}, so you won't need to repeat it.")


def start_escalation(db, emp, conv, intent, reason, chunks, steps, first_message, started):
    t, esc = escalate(db, emp, conv, intent, reason, chunks, steps, first_message)
    text = escalation_reply(intent, t.ticket_id, t.priority, emp.full_name.split()[0])
    blocks = [text_block(text, sources=article_sources(db, esc.summary.get("sources", [])[:2]) if intent in ("device_lost", "phishing_report") else []),
              {"type": "escalated", "ticket_id": t.ticket_id, "priority": t.priority, "group": t.assigned_group,
               "text": "Waiting for a technician"}]
    return blocks


def finish(db, conv, blocks, started, kb=None):
    latency = int((time.time() - started) * 1000)
    m = save(db, conv, "ai", " ".join(b.get("text", "") for b in blocks if b.get("type") == "text"), blocks, latency, kb)
    return m


def ask_for_code(db, emp, conv, function, args, intro):
    code = issue_otp(db, emp, function)
    conv.state = {"pending": {"function": function, "args": args, "otp": True}}
    return [{"type": "otp", "sent_to": f"****{emp.mobile_last4}", "expires_seconds": settings.otp_minutes * 60,
             "demo_code": code if settings.demo_mode else None}]


def do_verified_function(db, emp, conv, pending):
    name = pending["function"]
    t = run_function(db, emp, conv.conversation_id, name, pending.get("args", {}))
    conv.ticket_id = t.ticket_id
    conv.route = "Function"
    conv.state = {}
    if name == "unlock_account":
        title, text, tip = "Account unlocked", "Your account is unlocked and you can sign in again.", "Update your saved password on your phone and email app to avoid another lockout."
        src = "KB-ACC-001"
    elif name == "reset_password":
        title, text, tip = "Password reset", f"A temporary password was sent to your mobile ending ****{emp.mobile_last4}. You will set a new one at your next sign in.", "Use at least 12 characters with a number and a symbol."
        src = "KB-ACC-002"
    elif name == "reset_session":
        title, text, tip = "Citrix session reset", "Your Citrix session was reset. Wait about a minute, then launch it again.", "If Citrix is still slow, the Site 2 incident is the likely cause."
        src = "KB-APP-002"
    else:
        title, text, tip, src = "Done", "The request was completed.", "", "KB-014"
    return [{"type": "success", "title": title, "text": text, "tip": tip, "function": name,
             "ticket_id": t.ticket_id, "sources": article_sources(db, [src]), "feedback": True}]


def handle_action(db: Session, emp: Employee, conv: Conversation, action: str, code: str | None, value=None):
    started = time.time()
    pending = (conv.state or {}).get("pending")
    if action == "send_code" and pending:
        blocks = ask_for_code(db, emp, conv, pending["function"], pending.get("args", {}), "")
        return [finish(db, conv, blocks, started)]
    if action == "wait":
        conv.state = {}
        text = "No problem. The lock clears by itself in about 30 minutes. If you need it sooner, message me again." if pending and pending["function"] == "unlock_account" else "Okay, I'll stay here if you need me."
        return [finish(db, conv, [text_block(text)], started)]
    if action == "verify" and code is not None:
        if not pending:
            return [finish(db, conv, [text_block("There is no pending request. Tell me what you need help with.")], started)]
        save(db, conv, "user", "[verification code entered]")
        result = check_otp(db, emp, code)
        if result == "ok":
            blocks = do_verified_function(db, emp, conv, pending)
            return [finish(db, conv, blocks, started)]
        if result == "wrong":
            return [finish(db, conv, [text_block("That code is not correct. Check the message on your phone and try again.")] + [{"type": "otp", "sent_to": f"****{emp.mobile_last4}", "expires_seconds": settings.otp_minutes * 60, "demo_code": None, "retry": True}], started)]
        conv.state = {}
        log_guardrail(db, emp.employee_id, conv.conversation_id, "RBAC denied", "Verification failed", "Too many wrong or expired codes for a sensitive action")
        blocks = start_escalation(db, emp, conv, "human_request", "Identity could not be verified with a one-time code.", [],
                                  ["Sent a 6-digit code to the registered mobile.", "Code was wrong, expired or attempts ran out."],
                                  "I could not verify my identity for a sensitive request", started)
        return [finish(db, conv, [text_block("I could not verify the code, so I stopped the request for your safety.")] + blocks, started)]
    if action == "human":
        blocks = start_escalation(db, emp, conv, "human_request", "The agent asked to talk to a person.", [], [], "Asked to talk to a human", started)
        return [finish(db, conv, blocks, started)]
    if action == "resolved":
        first = db.query(Message).filter_by(conversation_id=conv.conversation_id, sender="user").first()
        summary = (first.content_redacted if first else "Resolved by Ridley")[:80]
        t = create_ticket(db, emp, summary, CATEGORY.get(conv.intent or "kb_question", "General"), PRIORITY.get(conv.intent or "kb_question", "P3"),
                          "AI Helpdesk", "Resolved", "AI")
        conv.ticket_id = t.ticket_id
        conv.route = "RAG"
        conv.csat = 5
        return [finish(db, conv, [text_block(f"Glad that worked. I logged it as {t.ticket_id} and closed it.")], started)]
    if action == "escalate":
        first = db.query(Message).filter_by(conversation_id=conv.conversation_id, sender="user").first()
        steps = ["Shared the matching SOP steps from the knowledge base.", "Agent said the problem is still there."]
        blocks = start_escalation(db, emp, conv, conv.intent if conv.intent not in (None, "kb_question") else "human_request",
                                  "The suggested steps did not fix the problem.", [], steps,
                                  first.content_redacted if first else "Issue not resolved", started)
        return [finish(db, conv, blocks, started)]
    if action == "rate" and value is not None:
        conv.csat = int(value)
        return []
    return [finish(db, conv, [text_block("I did not understand that action.")], started)]


def handle_message(db: Session, emp: Employee, conv: Conversation, text: str):
    started = time.time()
    clean, findings = redact_pii(text)
    created = []
    pending = (conv.state or {}).get("pending")

    if pending and pending.get("otp") and re.fullmatch(r"\d{6}", text.strip()):
        return handle_action(db, emp, conv, "verify", text.strip())

    user_msg = save(db, conv, "user", clean)
    created.append(user_msg)
    seen = set()
    for typ, detail in findings:
        if detail in seen:
            continue
        seen.add(detail)
        log_guardrail(db, emp.employee_id, conv.conversation_id, typ, detail, "Redacted before storage and before the AI call")
    if findings:
        created.append(save(db, conv, "system", "Guardrail", [{"type": "guardrail", "text": "Guardrail: sensitive data redacted before storage and AI"}]))

    if conv.human_active:
        return created

    if detect_injection(clean):
        log_guardrail(db, emp.employee_id, conv.conversation_id, "Injection blocked", "Message blocked", "Attempt to override instructions or reveal the system prompt")
        created.append(finish(db, conv, [text_block("I can't follow that request. I only help with IT support questions like accounts, VPN, telephony and access. What problem can I help you with?")], started))
        return created

    others = other_employee_ids(clean, emp.employee_id)
    if others and RESET_WORDS.search(clean):
        log_guardrail(db, emp.employee_id, conv.conversation_id, "RBAC denied", "Request denied", f"Attempt to reset another user's password ({others[0]})")
        created.append(finish(db, conv, [text_block("I can only act on your own account. A request for someone else has to come from that employee, or from the Service Desk.")], started))
        return created

    if (conv.state or {}).get("awaiting") == "application":
        app = clean.strip().rstrip(".")[:60]
        conv.state = {}
        t = run_function(db, emp, conv.conversation_id, "create_access_request", {"application": app})
        conv.ticket_id = t.ticket_id
        conv.route = "Function"
        created.append(finish(db, conv, [text_block(
            f"I've raised {t.ticket_id} for {app} access with the Identity and Access team. It takes up to 3 business days and your team lead will be asked to approve.",
            sources=article_sources(db, ["KB-APP-003"]))], started))
        return created

    intent, conf = classify_intent(clean)
    conv.intent = intent
    first = emp.full_name.split()[0]

    if intent in ("device_lost", "phishing_report", "human_request"):
        chunks = rag.search(clean, 2)
        blocks = start_escalation(db, emp, conv, intent, {"device_lost": "P1 policy: lost or stolen device.", "phishing_report": "Phishing reports are reviewed by Information Security.",
                                                           "human_request": "The agent asked for a person."}[intent], chunks, [], clean, started)
        created.append(finish(db, conv, blocks, started))
        return created

    if intent == "account_unlock":
        if emp.ad_locked:
            locked_at = emp.ad_locked_at or datetime.utcnow()
            conv.state = {"pending": {"function": "unlock_account", "args": {}}}
            conv.route = "Function"
            blocks = [text_block(
                f"Your account was locked at [[t:{locked_at.isoformat()}Z]] after 5 failed attempts. It unlocks on its own in 30 minutes, or I can unlock it now. "
                f"I'll send a 6-digit code to your mobile ending in ****{emp.mobile_last4}.",
                sources=article_sources(db, ["KB-ACC-001"]),
                actions=[{"label": "Send code", "action": "send_code", "style": "primary"}, {"label": "I'll wait", "action": "wait", "style": "ghost"}])]
        else:
            conv.state = {"pending": {"function": "reset_password", "args": {}}}
            blocks = [text_block(
                "I can't see a lock on your account right now, it shows as active. If you still can't sign in, the password may have expired. I can reset it after a quick verification.",
                sources=article_sources(db, ["KB-ACC-001", "KB-ACC-002"]),
                actions=[{"label": "Reset password", "action": "send_code", "style": "primary"}, {"label": "No thanks", "action": "wait", "style": "ghost"}])]
        created.append(finish(db, conv, blocks, started, "KB-ACC-001"))
        return created

    if intent == "password_reset":
        conv.state = {"pending": {"function": "reset_password", "args": {}}}
        conv.route = "Function"
        blocks = [text_block(
            f"I can reset your password. First I need to confirm it's you, so I'll send a 6-digit code to your mobile ending in ****{emp.mobile_last4}.",
            sources=article_sources(db, ["KB-ACC-002"]),
            actions=[{"label": "Send code", "action": "send_code", "style": "primary"}, {"label": "Not now", "action": "wait", "style": "ghost"}])]
        created.append(finish(db, conv, blocks, started, "KB-ACC-002"))
        return created

    if intent == "access_request":
        m = re.search(r"access (?:to|for|sa) (?:the |my )?([\w\s\-\./&]+?)(?:[\.,!\?]|$| please| pls| po)", clean, re.I)
        app = m.group(1).strip() if m else ""
        if not app or len(app) < 2:
            conv.state = {"awaiting": "application"}
            created.append(finish(db, conv, [text_block("Which application do you need access to? Tell me the name and I'll raise the request.", sources=article_sources(db, ["KB-APP-003"]))], started))
            return created
        t = run_function(db, emp, conv.conversation_id, "create_access_request", {"application": app})
        conv.ticket_id = t.ticket_id
        conv.route = "Function"
        created.append(finish(db, conv, [text_block(
            f"I've raised {t.ticket_id} for {app} access with the Identity and Access team. It takes up to 3 business days and your team lead will be asked to approve.",
            sources=article_sources(db, ["KB-APP-003"]))], started, "KB-APP-003"))
        return created

    chunks = rag.search(clean, 3)
    best = chunks[0]["score"] if chunks else 0
    if intent == "out_of_scope" or best < settings.retrieval_floor:
        if intent == "out_of_scope" or not chunks:
            conv.route = "RAG"
            created.append(finish(db, conv, [text_block(
                "That is outside what I can help with. I handle IT support for accounts, VPN, telephony, Citrix and access. I can connect you to a technician if you'd like.",
                actions=[{"label": "Talk to a human", "action": "human", "style": "primary"}])], started))
            return created
        blocks = start_escalation(db, emp, conv, "human_request", "No approved knowledge base article matched the question.", chunks,
                                  ["Searched the knowledge base and found no article above the confidence threshold."], clean, started)
        created.append(finish(db, conv, [text_block("I could not find an approved answer for that, and I don't want to guess.")] + blocks, started))
        return created

    answer = build_answer(clean, chunks, first)
    sources = source_list(db, chunks[:2])
    blocks = []
    inc = active_incident(db)
    if intent == "citrix_slow" and inc:
        answer = (f"There is an active incident: {inc.title} ({inc.incident_id}), next update {inc.next_update}. You do not need to file a separate ticket.\n\n" + answer)
        sources = article_sources(db, ["KB-015"]) + [s for s in sources if s["kb_id"] != "KB-015"]
        conv.state = {"pending": {"function": "reset_session", "args": {}}}
        actions = [{"label": "Reset my Citrix session", "action": "send_code", "style": "primary"},
                   {"label": "That fixed it", "action": "resolved", "style": "ghost"},
                   {"label": "Still not working", "action": "escalate", "style": "ghost"}]
    else:
        actions = [{"label": "That fixed it", "action": "resolved", "style": "primary"},
                   {"label": "Still not working", "action": "escalate", "style": "ghost"}]
    conv.route = "RAG"
    blocks.append(text_block(answer, sources=sources, actions=actions))
    created.append(finish(db, conv, blocks, started, chunks[0]["kb_id"]))
    return created
