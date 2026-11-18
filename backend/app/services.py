import random
import secrets
from datetime import datetime, timedelta

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from .config import settings
from .models import Employee, FunctionCall, GuardrailEvent, OtpCode, Ticket
from .security import hash_code

PRIORITY = {
    "account_unlock": "P2", "password_reset": "P2", "mfa_no_prompt": "P3", "vpn_issue": "P3",
    "wfh_internet": "P3", "softphone_audio": "P3", "call_drops": "P3", "citrix_slow": "P2",
    "access_request": "P4", "headset_issue": "P3", "device_lost": "P1", "phishing_report": "P2",
    "human_request": "P3", "kb_question": "P3", "out_of_scope": "P4",
}

GROUP = {
    "Accounts": "L1 Service Desk", "Access": "L2 Identity & Access", "Hardware": "IT Asset Management",
    "Telephony": "Telephony Support", "VPN / WFH": "Network Support", "Citrix / VDI": "Citrix / VDI Support",
    "Security": "Information Security", "General": "L1 Service Desk",
}

SLA_HOURS = {"P1": 4, "P2": 8, "P3": 48, "P4": 120}


def log_guardrail(db: Session, emp_id: str, conv_id, type_: str, action: str, detail: str):
    db.add(GuardrailEvent(employee_id=emp_id, conversation_id=conv_id, type=type_, action=action, detail=detail))


def log_function(db: Session, emp_id: str, conv_id, name: str, args: dict, result: str):
    db.add(FunctionCall(employee_id=emp_id, conversation_id=conv_id, function_name=name, arguments=args, result=result))


def next_ticket_id(db: Session) -> str:
    last = db.query(func.max(Ticket.ticket_id)).scalar()
    n = int(last.split("-")[1]) + 1 if last else 100001
    return f"TKT-{n}"


def create_ticket(db: Session, emp: Employee, summary: str, category: str, priority: str, group: str,
                  status: str = "Open", resolved_by=None, external_ref=None) -> Ticket:
    t = Ticket(
        ticket_id=next_ticket_id(db), employee_id=emp.employee_id, summary=summary[:190], category=category,
        priority=priority, status=status, assigned_group=group, resolved_by=resolved_by,
        created_at=datetime.utcnow(), external_ref=external_ref,
        resolved_at=datetime.utcnow() if status == "Resolved" else None,
    )
    db.add(t)
    db.flush()
    return t


def sla_text(t: Ticket) -> str:
    if t.status == "Resolved":
        if t.resolved_by == "AI" and t.resolved_at:
            mins = max(1, round((t.resolved_at - t.created_at).total_seconds() / 60))
            return f"Resolved by Ridley in {mins} min"
        return "Resolved"
    if t.priority in ("P3", "P4"):
        days = 2 if t.priority == "P3" else 5
        due = t.created_at + timedelta(days=days)
        left = due - datetime.utcnow()
        if left.total_seconds() <= 0:
            return "Past target"
        if left.days >= 1:
            return f"{left.days}d {left.seconds // 3600}h left"
        return f"{left.seconds // 3600}h left"
    due = t.created_at + timedelta(hours=SLA_HOURS[t.priority])
    left = due - datetime.utcnow()
    if left.total_seconds() <= 0:
        return "Past target"
    return f"{int(left.total_seconds() // 3600)}h {int(left.total_seconds() % 3600 // 60)}m left"


def sla_breached(t: Ticket) -> bool:
    if t.status in ("Resolved", "Redirected"):
        return False
    return (datetime.utcnow() - t.created_at) > timedelta(hours=SLA_HOURS[t.priority])


def call_webhook(name: str, payload: dict) -> str:
    if not settings.n8n_webhook_url:
        return "simulated"
    try:
        r = httpx.post(f"{settings.n8n_webhook_url.rstrip('/')}/{name}", json=payload, timeout=4)
        return "n8n" if r.status_code < 400 else "n8n-error"
    except Exception:
        return "n8n-unreachable"


def issue_otp(db: Session, emp: Employee, purpose: str):
    db.query(OtpCode).filter(OtpCode.employee_id == emp.employee_id, OtpCode.used.is_(False)).update({"used": True})
    code = f"{secrets.randbelow(900000) + 100000}"
    db.add(OtpCode(employee_id=emp.employee_id, purpose=purpose, code_hash=hash_code(code),
                   expires_at=datetime.utcnow() + timedelta(minutes=settings.otp_minutes)))
    call_webhook("send_otp", {"employee_id": emp.employee_id, "mobile_last4": emp.mobile_last4, "purpose": purpose})
    return code


def check_otp(db: Session, emp: Employee, code: str):
    otp = (db.query(OtpCode).filter(OtpCode.employee_id == emp.employee_id, OtpCode.used.is_(False))
           .order_by(OtpCode.otp_id.desc()).first())
    if otp is None:
        return "none"
    if otp.expires_at < datetime.utcnow():
        otp.used = True
        return "expired"
    if otp.attempts >= settings.otp_max_attempts:
        otp.used = True
        return "locked"
    if otp.code_hash != hash_code(code):
        otp.attempts += 1
        if otp.attempts >= settings.otp_max_attempts:
            otp.used = True
            return "locked"
        return "wrong"
    otp.used = True
    return "ok"


def run_function(db: Session, emp: Employee, conv_id, name: str, args: dict):
    ref = call_webhook(name, {"employee_id": emp.employee_id, **args})
    if name == "unlock_account":
        emp.ad_locked = False
        emp.ad_locked_at = None
        t = create_ticket(db, emp, "Account locked", "Accounts", "P2", "AI Helpdesk", "Resolved", "AI")
        result = f"Success ({ref})"
    elif name == "reset_password":
        t = create_ticket(db, emp, "Password reset", "Accounts", "P2", "AI Helpdesk", "Resolved", "AI")
        result = f"Success ({ref})"
    elif name == "reset_session":
        t = create_ticket(db, emp, "Citrix session frozen, session reset", "Citrix / VDI", "P2", "AI Helpdesk", "Resolved", "AI")
        result = f"Success ({ref})"
    elif name == "create_access_request":
        app = args.get("application", "application")
        t = create_ticket(db, emp, f"Need {app} access", "Access", "P4", "L2 Identity & Access", "Open",
                          external_ref=f"ITSD-{random.randint(1000, 9999)}")
        result = f"Success ({ref})"
    else:
        raise ValueError(name)
    log_function(db, emp.employee_id, conv_id, name, args, result)
    return t


def initials(name: str) -> str:
    parts = name.split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else name[:2].upper()
