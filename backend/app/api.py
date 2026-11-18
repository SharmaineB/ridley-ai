import csv
import io
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from . import chat_flow, rag
from .config import settings
from .db import get_db
from .guardrails import redact_pii
from .models import (ClientAccount, Conversation, Employee, Escalation, FunctionCall, GuardrailEvent, Incident,
                     KBArticle, Message, Ticket)
from .security import current_user, make_token, require, verify_password
from .services import GROUP, initials, log_guardrail, sla_breached, sla_text

router = APIRouter(prefix="/api")

INTENT_KB = {
    "mfa_no_prompt": "KB-ACC-006", "citrix_slow": "KB-APP-002", "phishing_report": "KB-SEC-001", "headset_issue": "KB-HW-001",
    "account_unlock": "KB-ACC-001", "password_reset": "KB-ACC-002", "softphone_audio": "KB-TEL-001", "call_drops": "KB-TEL-003",
    "vpn_issue": "KB-NET-001", "wfh_internet": "KB-NET-004", "access_request": "KB-APP-003", "device_lost": "KB-HW-003",
    "human_request": "KB-014", "kb_question": "KB-014", "out_of_scope": "KB-014",
}
FUNCTION_INTENTS = {"account_unlock", "password_reset", "access_request"}


def iso(dt):
    return dt.isoformat() + "Z" if dt else None


def user_out(e: Employee):
    return {"employee_id": e.employee_id, "full_name": e.full_name, "first_name": e.full_name.split()[0], "role": e.role,
            "title": e.title, "initials": initials(e.full_name), "account": e.account.name if e.account else None,
            "site": e.site, "work_mode": e.work_mode, "mobile_last4": e.mobile_last4}


def msg_out(m: Message):
    return {"message_id": m.message_id, "sender": m.sender, "text": m.content_redacted, "blocks": m.blocks or [],
            "created_at": iso(m.created_at)}


def ticket_out(t: Ticket):
    return {"ticket_id": t.ticket_id, "summary": t.summary, "category": t.category, "priority": t.priority, "status": t.status,
            "assigned_group": t.assigned_group, "resolved_by": t.resolved_by, "created_at": iso(t.created_at),
            "sla": sla_text(t), "breached": sla_breached(t), "employee_id": t.employee_id,
            "employee_name": t.employee.full_name if t.employee else "", "account": t.employee.account.name if t.employee and t.employee.account else ""}


class LoginIn(BaseModel):
    employee_id: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    emp = db.get(Employee, body.employee_id.strip().upper())
    if emp is None or not verify_password(body.password, emp.password_hash):
        raise HTTPException(401, "Incorrect Employee ID or password.")
    return {"token": make_token(emp), "user": user_out(emp)}


@router.get("/auth/me")
def me(user: Employee = Depends(current_user)):
    return user_out(user)


@router.get("/banner")
def banner(user: Employee = Depends(current_user), db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.active.is_(True)).first()
    if not inc:
        return {"incident": None}
    return {"incident": {"id": inc.incident_id, "title": inc.title, "site": inc.site, "next_update": inc.next_update}}


class ChatIn(BaseModel):
    conversation_id: str | None = None
    message: str | None = None
    action: str | None = None
    code: str | None = None
    value: int | None = None


@router.post("/chat")
def chat(body: ChatIn, user: Employee = Depends(require("agent")), db: Session = Depends(get_db)):
    conv = db.get(Conversation, body.conversation_id) if body.conversation_id else None
    if conv is not None and conv.employee_id != user.employee_id:
        raise HTTPException(403, "This conversation belongs to someone else")
    if conv is None:
        conv = chat_flow.new_conversation(db, user)
    if body.action:
        created = chat_flow.handle_action(db, user, conv, body.action, body.code, body.value)
    elif body.message and body.message.strip():
        created = chat_flow.handle_message(db, user, conv, body.message.strip()[:2000])
    else:
        raise HTTPException(400, "Empty message")
    db.commit()
    return {"conversation_id": conv.conversation_id, "human_active": conv.human_active, "messages": [msg_out(m) for m in created]}


@router.get("/conversations/{cid}")
def conversation(cid: str, user: Employee = Depends(current_user), db: Session = Depends(get_db)):
    conv = db.get(Conversation, cid)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    if user.role == "agent" and conv.employee_id != user.employee_id:
        raise HTTPException(403, "This conversation belongs to someone else")
    rows = db.query(Message).filter_by(conversation_id=cid).order_by(Message.message_id).all()
    rows = [m for m in rows if m.content_redacted or m.blocks]
    return {"conversation_id": cid, "human_active": conv.human_active, "ticket_id": conv.ticket_id,
            "messages": [msg_out(m) for m in rows]}


@router.get("/conversations")
def latest_conversation(user: Employee = Depends(require("agent")), db: Session = Depends(get_db)):
    conv = (db.query(Conversation).join(Message, Message.conversation_id == Conversation.conversation_id)
            .filter(Conversation.employee_id == user.employee_id, Message.content_redacted != "")
            .order_by(Conversation.started_at.desc()).first())
    return {"conversation_id": conv.conversation_id if conv else None}


@router.post("/demo/lock-me")
def lock_me(user: Employee = Depends(require("agent")), db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(404, "Not available")
    user.ad_locked = True
    user.ad_locked_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/tickets")
def my_tickets(status: str | None = None, priority: str | None = None, user: Employee = Depends(require("agent")),
               db: Session = Depends(get_db)):
    base = db.query(Ticket).filter(Ticket.employee_id == user.employee_id)
    allrows = base.all()
    q = base
    if status and status != "All":
        q = q.filter(Ticket.status == status)
    if priority and priority != "All":
        q = q.filter(Ticket.priority == priority)
    rows = q.order_by(Ticket.created_at.desc()).all()
    resolved = [t for t in allrows if t.status == "Resolved"]
    ai = [t for t in resolved if t.resolved_by == "AI"]
    since = min((t.created_at for t in allrows), default=datetime.utcnow())
    return {
        "tickets": [ticket_out(t) for t in rows],
        "counts": {
            "open": sum(1 for t in allrows if t.status == "Open"),
            "in_progress": sum(1 for t in allrows if t.status in ("In Progress", "Escalated")),
            "resolved_by_ridley": len(ai), "resolved_total": len(resolved), "all": len(allrows),
            "since": since.strftime("%b %Y"),
        },
    }


def wait_minutes(esc: Escalation):
    return max(0, int((datetime.utcnow() - esc.created_at).total_seconds() // 60))


def esc_card(e: Escalation):
    t = e.ticket
    return {"escalation_id": e.escalation_id, "ticket_id": t.ticket_id, "priority": t.priority, "status": e.status,
            "employee_name": t.employee.full_name, "employee_id": t.employee_id, "issue": t.summary,
            "wait_min": wait_minutes(e), "assigned_group": t.assigned_group, "technician_id": e.technician_id,
            "ack_due": "13:00" if t.priority == "P1" else None}


@router.get("/escalations")
def escalations(user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    rows = db.query(Escalation).filter(Escalation.status.in_(["Waiting", "In progress"])).all()
    rows.sort(key=lambda e: (e.ticket.priority, e.created_at))
    return {"escalations": [esc_card(e) for e in rows], "waiting": sum(1 for e in rows if e.status == "Waiting")}


@router.get("/escalations/{eid}")
def escalation_detail(eid: int, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    e = db.get(Escalation, eid)
    if e is None:
        raise HTTPException(404, "Escalation not found")
    msgs = db.query(Message).filter_by(conversation_id=e.conversation_id).order_by(Message.message_id).all()
    msgs = [m for m in msgs if m.content_redacted or m.blocks]
    return {**esc_card(e), "summary": e.summary, "human_active": e.conversation.human_active, "external_ref": e.external_ref,
            "messages": [msg_out(m) for m in msgs]}


def get_esc(db, eid):
    e = db.get(Escalation, eid)
    if e is None:
        raise HTTPException(404, "Escalation not found")
    return e


@router.post("/escalations/{eid}/takeover")
def takeover(eid: int, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    e = get_esc(db, eid)
    e.technician_id = user.employee_id
    e.status = "In progress"
    e.taken_over_at = datetime.utcnow()
    e.ticket.status = "In Progress"
    e.conversation.human_active = True
    db.add(Message(conversation_id=e.conversation_id, sender="system", content_redacted="Technician joined",
                   blocks=[{"type": "joined", "text": f"{user.full_name} joined the chat"}]))
    db.commit()
    return {"ok": True}


class TechMessage(BaseModel):
    text: str


@router.post("/escalations/{eid}/message")
def tech_message(eid: int, body: TechMessage, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    e = get_esc(db, eid)
    if e.technician_id is None:
        raise HTTPException(409, "Take over the chat first")
    clean, _ = redact_pii(body.text.strip()[:2000])
    db.add(Message(conversation_id=e.conversation_id, sender="tech", content_redacted=clean))
    db.commit()
    return {"ok": True}


@router.post("/escalations/{eid}/resolve")
def resolve(eid: int, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    e = get_esc(db, eid)
    e.status = "Resolved"
    e.ticket.status = "Resolved"
    e.ticket.resolved_by = "Human"
    e.ticket.resolved_at = datetime.utcnow()
    e.conversation.human_active = False
    db.add(Message(conversation_id=e.conversation_id, sender="system", content_redacted="Ticket resolved",
                   blocks=[{"type": "joined", "text": f"{user.full_name} resolved {e.ticket_id}"}]))
    db.commit()
    return {"ok": True}


class Reassign(BaseModel):
    group: str


@router.post("/escalations/{eid}/reassign")
def reassign(eid: int, body: Reassign, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    e = get_esc(db, eid)
    e.ticket.assigned_group = body.group
    summary = dict(e.summary)
    summary["recommended_group"] = body.group
    e.summary = summary
    db.commit()
    return {"ok": True, "groups": sorted(set(GROUP.values()))}


@router.get("/meta/groups")
def groups(user: Employee = Depends(current_user)):
    return {"groups": sorted(set(GROUP.values()))}


def week_start(d: datetime):
    d0 = d - timedelta(days=d.weekday())
    return d0.replace(hour=0, minute=0, second=0, microsecond=0)


def account_filter(db, account):
    if not account or account == "All accounts":
        return None
    acc = db.query(ClientAccount).filter_by(name=account).first()
    return acc.account_id if acc else None


@router.get("/admin/metrics")
def metrics(account: str | None = None, days: int | None = None, user: Employee = Depends(require("admin")),
            db: Session = Depends(get_db)):
    aid = account_filter(db, account)
    tq = db.query(Ticket).join(Employee, Employee.employee_id == Ticket.employee_id)
    if aid:
        tq = tq.filter(Employee.account_id == aid)
    if days:
        tq = tq.filter(Ticket.created_at >= datetime.utcnow() - timedelta(days=days))
    tickets = tq.all()
    total = len(tickets)
    ai = [t for t in tickets if t.status == "Resolved" and t.resolved_by == "AI"]
    resolved = [t for t in tickets if t.status == "Resolved" and t.resolved_at]
    mttr_h = statistics.mean((t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved) if resolved else 0
    ids = {t.ticket_id for t in tickets}
    convs = db.query(Conversation).filter(Conversation.ticket_id.in_(ids)).all() if ids else []
    cids = [c.conversation_id for c in convs]
    lat = []
    if cids:
        for chunk in range(0, len(cids), 500):
            lat += [m.latency_ms for m in db.query(Message).filter(Message.conversation_id.in_(cids[chunk:chunk + 500]),
                                                                  Message.latency_ms.isnot(None)).all()]
    lat.sort()
    p95 = lat[int(len(lat) * 0.95) - 1] / 1000 if lat else 0
    ratings = [c.csat for c in convs if c.csat]
    weekly = defaultdict(lambda: [0, 0])
    for t in tickets:
        w = week_start(t.created_at)
        if t.status == "Resolved" and t.resolved_by == "AI":
            weekly[w][0] += 1
        else:
            weekly[w][1] += 1
    now_w = week_start(datetime.utcnow())
    weeks = sorted(w for w in weekly if w < now_w) or sorted(weekly)
    cat_count = Counter(t.category for t in tickets)
    since = datetime.utcnow() - timedelta(days=14)
    recent = [c for c in convs if c.started_at >= since] or convs
    tmap = {t.ticket_id: t for t in tickets}
    by_intent = defaultdict(list)
    for c in recent:
        by_intent[c.intent].append(c)
    top = []
    for intent, cs in by_intent.items():
        ex = Counter(tmap[c.ticket_id].summary for c in cs if c.ticket_id in tmap).most_common(1)
        route = Counter(c.route for c in cs).most_common(1)[0][0]
        top.append({"intent": intent, "example": ex[0][0] if ex else "", "kb": INTENT_KB.get(intent, "KB-014"),
                    "route": "Function" if intent in FUNCTION_INTENTS and route != "Escalate" else ("Escalate" if route == "Escalate" else "RAG"),
                    "count": len(cs)})
    top.sort(key=lambda r: -r["count"])
    first = min((t.created_at for t in tickets), default=datetime.utcnow())
    return {
        "deflection_rate": round(100 * len(ai) / total, 1) if total else 0, "ai_resolved": len(ai), "total": total,
        "mttr_hours": round(mttr_h, 1), "p95_latency_s": round(p95, 1), "latency_samples": len(lat),
        "csat": round(statistics.mean(ratings), 1) if ratings else 0, "csat_count": len(ratings),
        "weekly": [{"week": w.strftime("%b %d"), "ai": weekly[w][0], "escalated": weekly[w][1]} for w in weeks],
        "categories": [{"name": n, "count": c} for n, c in cat_count.most_common(6)],
        "top_intents": top[:6], "range": {"start": iso(first), "end": iso(datetime.utcnow())},
    }


@router.get("/admin/tickets")
def all_tickets(q: str | None = None, status: str | None = None, priority: str | None = None, account: str | None = None,
                page: int = 1, page_size: int = 10, export: bool = False,
                user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    base = db.query(Ticket).join(Employee, Employee.employee_id == Ticket.employee_id)
    aid = account_filter(db, account)
    if aid:
        base = base.filter(Employee.account_id == aid)
    allrows = base.all()
    qq = base
    if status and status != "All":
        qq = qq.filter(Ticket.status == status)
    if priority and priority != "All":
        qq = qq.filter(Ticket.priority == priority)
    if q:
        like = f"%{q.strip()}%"
        qq = qq.filter(or_(Ticket.ticket_id.ilike(like), Ticket.summary.ilike(like), Employee.full_name.ilike(like), Employee.employee_id.ilike(like)))
    qq = qq.order_by(Ticket.created_at.desc())
    if export:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["ticket_id", "employee_id", "employee", "account", "summary", "category", "priority", "status", "group", "created_at", "resolved_by"])
        for t in qq.all():
            w.writerow([t.ticket_id, t.employee_id, t.employee.full_name, t.employee.account.name if t.employee.account else "", t.summary,
                        t.category, t.priority, t.status, t.assigned_group, iso(t.created_at), t.resolved_by or ""])
        out.seek(0)
        return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tickets.csv"})
    total = qq.count()
    rows = qq.offset((max(page, 1) - 1) * page_size).limit(page_size).all()
    ai = sum(1 for t in allrows if t.status == "Resolved" and t.resolved_by == "AI")
    return {
        "tickets": [ticket_out(t) for t in rows], "total": total, "page": page, "page_size": page_size,
        "stats": {"tickets": len(allrows), "employees": len({t.employee_id for t in allrows}),
                  "open_now": sum(1 for t in allrows if t.status in ("Open", "In Progress", "Escalated")), "resolved_by_ridley": ai,
                  "ridley_pct": round(100 * ai / len(allrows), 1) if allrows else 0, "sla_breached": sum(1 for t in allrows if sla_breached(t))},
    }


def kb_row(a: KBArticle):
    return {"id": a.id, "kb_id": a.kb_id, "title": a.title, "category": a.category, "version": a.version, "status": a.status,
            "updated_at": iso(a.updated_at)}


@router.get("/kb/articles")
def kb_list(user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    rows = db.query(KBArticle).order_by(KBArticle.kb_id, KBArticle.id.desc()).all()
    active = sum(1 for a in rows if a.status == "active")
    last = max((a.updated_at for a in rows), default=None)
    return {"articles": [kb_row(a) for a in rows],
            "stats": {"documents": len(rows), "active": active, "superseded": len(rows) - active, "last_index": iso(last)}}


@router.get("/kb/articles/{aid}")
def kb_get(aid: int, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    a = db.get(KBArticle, aid)
    if a is None:
        raise HTTPException(404, "Article not found")
    return {**kb_row(a), "body": a.body}


class KBIn(BaseModel):
    kb_id: str
    title: str
    category: str
    body: str


@router.post("/kb/articles")
def kb_upload(body: KBIn, user: Employee = Depends(require("admin")), db: Session = Depends(get_db)):
    kid = body.kb_id.strip().upper()
    prev = db.query(KBArticle).filter(KBArticle.kb_id == kid, KBArticle.status == "active").all()
    ver = 1
    for p in prev:
        p.status = "superseded"
        try:
            ver = max(ver, int(p.version.lstrip("v").split(".")[0]) + 1)
        except ValueError:
            ver = ver + 1
    art = KBArticle(kb_id=kid, version=f"v{ver}.0", title=body.title.strip(), category=body.category.strip(), body=body.body,
                    status="active", updated_at=datetime.utcnow())
    db.add(art)
    db.commit()
    chunks = rag.index_all(db)
    return {"ok": True, "article": kb_row(art), "chunks": chunks}


@router.post("/kb/reindex")
def kb_reindex(user: Employee = Depends(require("admin")), db: Session = Depends(get_db)):
    return {"chunks": rag.index_all(db)}


class TestIn(BaseModel):
    query: str


@router.post("/kb/test-retrieval")
def kb_test(body: TestIn, user: Employee = Depends(require("technician", "admin")), db: Session = Depends(get_db)):
    started = datetime.utcnow()
    active, filtered = rag.search(body.query, 3, include_inactive=True)
    from .llm import build_answer
    answer = build_answer(body.query, active, "Agent") if active and active[0]["score"] >= settings.retrieval_floor else ""
    ms = int((datetime.utcnow() - started).total_seconds() * 1000)
    return {"query": body.query, "elapsed_ms": ms, "results": active, "filtered": filtered, "answer": answer,
            "sources": [a["kb_id"] for a in active[:1]]}


def audit_query(db, tab, type_, start, end):
    model = GuardrailEvent if tab == "guardrail" else FunctionCall
    q = db.query(model)
    col = model.created_at if tab == "guardrail" else model.called_at
    if type_ and type_ != "All":
        q = q.filter((GuardrailEvent.type if tab == "guardrail" else FunctionCall.function_name) == type_)
    if start:
        q = q.filter(col >= datetime.fromisoformat(start))
    if end:
        q = q.filter(col < datetime.fromisoformat(end) + timedelta(days=1))
    return q.order_by(col.desc()), col


@router.get("/audit")
def audit(tab: str = "guardrail", type: str | None = None, start: str | None = None, end: str | None = None,
          page: int = 1, page_size: int = 15, export: bool = False,
          user: Employee = Depends(require("admin")), db: Session = Depends(get_db)):
    q, col = audit_query(db, tab, type, start, end)
    names = {e.employee_id: e.full_name for e in db.query(Employee).all()}
    if export:
        out = io.StringIO()
        w = csv.writer(out)
        if tab == "guardrail":
            w.writerow(["time", "employee", "type", "action", "detail"])
            for r in q.all():
                w.writerow([iso(r.created_at), r.employee_id, r.type, r.action, r.detail])
        else:
            w.writerow(["time", "employee", "function", "arguments", "result"])
            for r in q.all():
                w.writerow([iso(r.called_at), r.employee_id, r.function_name, r.arguments, r.result])
        return StreamingResponse(iter([out.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=audit-{tab}.csv"})
    total = q.count()
    rows = q.offset((max(page, 1) - 1) * page_size).limit(page_size).all()
    if tab == "guardrail":
        items = [{"time": iso(r.created_at), "employee": names.get(r.employee_id, r.employee_id), "employee_id": r.employee_id,
                  "type": r.type, "action": r.action, "detail": r.detail} for r in rows]
        types = [t[0] for t in db.query(GuardrailEvent.type).distinct().all()]
    else:
        items = [{"time": iso(r.called_at), "employee": names.get(r.employee_id, r.employee_id), "employee_id": r.employee_id,
                  "function": r.function_name, "arguments": r.arguments, "result": r.result} for r in rows]
        types = [t[0] for t in db.query(FunctionCall.function_name).distinct().all()]
    counts = {"guardrail": db.query(GuardrailEvent).count(), "function": db.query(FunctionCall).count()}
    return {"items": items, "total": total, "page": page, "page_size": page_size, "types": sorted(types), "counts": counts}


@router.get("/health")
def health():
    return {"ok": True, "llm": "openai" if settings.openai_api_key else "local-fallback", "vector_backend": rag.backend_name(),
            "n8n": bool(settings.n8n_webhook_url)}
