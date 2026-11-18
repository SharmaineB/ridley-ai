import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from . import rag
from .kb_data import KB_ARTICLES
from .models import (ClientAccount, Conversation, Employee, Escalation, FunctionCall, GuardrailEvent, Incident, KBArticle, Message, Ticket)
from .security import hash_password
from .summary import build_summary

PASSWORD = "ridley2026"

FIRST = ["Maria", "Jose", "Angelica", "Mark", "Patricia", "John", "Ivy", "Paolo", "Camille", "Rico", "Bianca", "Jerome", "Nicole",
         "Gabriel", "Trisha", "Dennis", "Kyla", "Ramon", "Hazel", "Luis", "Janine", "Vince", "Alyssa", "Marco", "Denise",
         "Carl", "Shiela", "Joel", "Mika", "Arnel", "Liza", "Noel", "Cathy", "Ryan"]
LAST = ["Garcia", "Reyes", "Ramos", "Mendoza", "Santos", "Flores", "Gonzales", "Bautista", "Villanueva", "Aquino", "Castillo",
        "Navarro", "Torres", "Domingo", "Pascual", "Soriano", "Lim", "Tan", "Manalo", "Cruz", "Estrada", "Delos Santos"]

CATS = [
    ("Accounts", 175, ["Account locked", "Password reset", "MFA prompt not received, new phone", "Locked out after failed logins", "Password expired"], "P2", "account_unlock", 0.9),
    ("Telephony", 104, ["Softphone no audio", "Calls dropping every few minutes", "One-way audio on calls", "Softphone will not sign in"], "P3", "softphone_audio", 0.5),
    ("VPN / WFH", 83, ["VPN session timeout", "VPN error VPN-301", "Slow home internet during shift", "VPN keeps disconnecting"], "P3", "vpn_issue", 0.6),
    ("Access", 76, ["Need CRM access", "Need shared drive access", "Access to reporting tool", "Need ticketing tool access"], "P4", "access_request", 0.1),
    ("Citrix / VDI", 60, ["Citrix very laggy", "Citrix session frozen", "Citrix will not launch"], "P2", "citrix_slow", 0.3),
    ("Hardware", 38, ["Headset mic not working", "Headset no sound", "Mouse not detected"], "P3", "headset_issue", 0.25),
    ("Security", 40, ["Phishing email reported", "Suspicious link in email", "Account disabled"], "P2", "phishing_report", 0.05),
    ("General", 24, ["Monitor flickering", "Keyboard keys not working", "Printer not found"], "P3", "kb_question", 0.0),
]
GROUPS = {"Accounts": "L1 Service Desk", "Telephony": "Telephony Support", "VPN / WFH": "Network Support", "Access": "L2 Identity & Access",
          "Citrix / VDI": "Citrix / VDI Support", "Hardware": "IT Asset Management", "Security": "Information Security", "General": "L1 Service Desk"}


def seed(db: Session):
    if db.query(Employee).count():
        return
    rnd = random.Random(2026)
    now = datetime.utcnow()
    pw = hash_password(PASSWORD)

    accounts = [ClientAccount(account_id=1, name="PayNova", sla_minutes=240), ClientAccount(account_id=2, name="ShopLoop", sla_minutes=240),
                ClientAccount(account_id=3, name="ClearFeed", sla_minutes=480)]
    db.add_all(accounts)

    def emp(eid, name, role, title, acct, site="Site 2", mode="On-site", laptop="", last4=None):
        return Employee(employee_id=eid, account_id=acct, full_name=name, role=role, title=title, site=site, work_mode=mode,
                        password_hash=pw, mobile_hash="", mobile_last4=last4 or f"{rnd.randint(1000, 9999)}", laptop=laptop)

    demo = [
        emp("NX-20004", "Kristine Dela Cruz", "agent", "Agent", 2, laptop="LT-2004", last4="4417"),
        emp("NX-20007", "Carlo Santos", "agent", "Agent", 1, laptop="LT-3007"),
        emp("NX-20011", "Princess Rivera", "agent", "Agent", 3, laptop="LT-2011"),
        emp("NX-20015", "Christian Lopez", "agent", "Agent", 1, laptop="LT-2015"),
        emp("NX-20021", "Rhea Salazar", "agent", "Agent", 2, mode="Work from home", laptop="LT-2021"),
        emp("NX-30001", "Miguel Torres", "technician", "L1 Technician", None, laptop="LT-1001"),
        emp("NX-30002", "Joanna Reyes", "technician", "L2 Technician", None, laptop="LT-1002"),
        emp("NX-90001", "Ana Villanueva", "admin", "IT Administrator", None, laptop="LT-0001"),
    ]
    demo[0].ad_locked = True
    demo[0].ad_locked_at = now - timedelta(minutes=2)
    db.add_all(demo)
    agents = [e for e in demo if e.role == "agent"]
    for i in range(34):
        name = f"{FIRST[i % len(FIRST)]} {rnd.choice(LAST)}"
        e = emp(f"NX-{20030 + i * 3}", name, "agent", "Agent", rnd.choice([1, 2, 3]), site=rnd.choice(["Site 1", "Site 2", "Site 3"]),
                mode=rnd.choice(["On-site", "On-site", "Work from home"]), laptop=f"LT-{2030 + i * 3}")
        db.add(e)
        agents.append(e)
    db.flush()

    for a in KB_ARTICLES:
        db.add(KBArticle(kb_id=a["kb_id"], version=a["version"], title=a["title"], category=a["category"], body=a["body"],
                         status=a.get("status", "active"), updated_at=now - timedelta(days=rnd.randint(2, 30))))
    db.add(Incident(incident_id="INC-2026-1187", title="Citrix degraded at Site 2", site="Site 2", next_update="10:00", active=True))

    tickets, convs, msgs = [], [], []
    total = 0
    n = 100000
    weights = []
    for cat, count, summ, prio, intent, ai_rate in CATS:
        weights.extend([(cat, summ, prio, intent, ai_rate)] * count)
    rnd.shuffle(weights)
    span_days = 112
    for cat, summ, prio, intent, ai_rate in weights:
        n += 1
        agent = rnd.choice(agents)
        created = now - timedelta(days=rnd.random() * span_days, minutes=rnd.randint(0, 600))
        ai = rnd.random() < ai_rate
        recent = (now - created).days < 3
        if ai:
            status, by = "Resolved", "AI"
            resolved = created + timedelta(minutes=rnd.randint(1, 6))
            group = "AI Helpdesk"
        else:
            by = "Human"
            group = GROUPS[cat]
            if recent and rnd.random() < 0.5:
                status = rnd.choice(["Open", "In Progress", "Escalated"])
                resolved = None
                by = None
            else:
                status = "Resolved" if rnd.random() < 0.94 else "Redirected"
                resolved = created + timedelta(hours=rnd.randint(1, 40)) if status == "Resolved" else None
                if status == "Redirected":
                    by = None
        tid = f"TKT-{n}"
        tickets.append(dict(ticket_id=tid, employee_id=agent.employee_id, summary=rnd.choice(summ), category=cat,
                            priority=prio if rnd.random() < 0.8 else rnd.choice(["P2", "P3", "P4"]), status=status,
                            assigned_group=group, resolved_by=by, created_at=created, resolved_at=resolved, external_ref=None))
        cid = uuid.uuid4().hex[:16]
        convs.append(dict(conversation_id=cid, employee_id=agent.employee_id, ticket_id=tid, intent=intent,
                          route="Function" if (ai and cat == "Accounts") else ("RAG" if ai else "Escalate"),
                          csat=(rnd.choice([4, 4, 5, 5, 5, 3]) if ai else (rnd.choice([2, 3, 3, 4]) if rnd.random() < 0.5 else None)),
                          state={}, human_active=False, started_at=created))
        lat = int(min(4600, max(900, rnd.gauss(2100, 750))))
        if rnd.random() < 0.06:
            lat = rnd.randint(3500, 4300)
        msgs.append(dict(conversation_id=cid, sender="ai", content_redacted="", blocks=None, kb_article_id=None, latency_ms=lat, created_at=created))
    db.bulk_insert_mappings(Ticket, tickets)
    db.bulk_insert_mappings(Conversation, convs)
    db.bulk_insert_mappings(Message, msgs)
    db.flush()

    calls = []
    for tk, cv in zip(tickets, convs):
        if tk["resolved_by"] != "AI":
            continue
        fn = {"Accounts": rnd.choice(["unlock_account", "unlock_account", "reset_password"]), "Access": "create_access_request",
              "Citrix / VDI": "reset_session"}.get(tk["category"])
        if fn:
            calls.append(dict(conversation_id=cv["conversation_id"], employee_id=tk["employee_id"], function_name=fn,
                              arguments={"employee_id": tk["employee_id"]}, result="Success (simulated)", called_at=tk["created_at"]))
    db.bulk_insert_mappings(FunctionCall, calls)
    kinds = [("PII redacted", "Redacted", "Card number redacted"), ("PII redacted", "Redacted", "Phone number redacted"),
             ("PII redacted", "Redacted", "Email address redacted"), ("Injection blocked", "Message blocked", "Attempt to reveal the system prompt"),
             ("Injection blocked", "Message blocked", "Instruction override attempt"), ("RBAC denied", "Request denied", "Attempt to reset another user's password")]
    events = []
    for _ in range(46):
        k = rnd.choice(kinds)
        events.append(dict(conversation_id=None, employee_id=rnd.choice(agents).employee_id, type=k[0], action=k[1], detail=k[2],
                           created_at=now - timedelta(days=rnd.random() * 60, minutes=rnd.randint(0, 900))))
    db.bulk_insert_mappings(GuardrailEvent, events)

    n = 100602
    kd = demo[0]
    extras = [
        ("TKT-100601", kd, "Need ShopLoop CRM access", "Access", "P4", "Open", "L2 Identity & Access", None, now - timedelta(hours=20)),
        ("TKT-100602", kd, "Headset mic not working", "Hardware", "P3", "In Progress", "IT Asset Management", None, now - timedelta(hours=30)),
    ]
    for tid, e, summ, cat, prio, st, grp, by, created in extras:
        db.add(Ticket(ticket_id=tid, employee_id=e.employee_id, summary=summ, category=cat, priority=prio, status=st,
                      assigned_group=grp, resolved_by=by, created_at=created))
    db.flush()

    cases = [
        (demo[1], "device_lost", "P1", "Information Security", "Laptop stolen", 2, [
            ("user", "nanakaw yung laptop ko sa kotse, please help. pls call me at [PHONE REDACTED]"),
            ("ai", "I'm sorry that happened. I hope you're okay. I've created priority ticket and alerted Security, who will lock and wipe the laptop remotely. Please tell your team lead and get a police report within 48 hours."),
            ("user", "will i be charged for it? my shift starts at 10, what laptop do i use"),
            ("ai", "This needs a person from our team, so I'm connecting you to a technician now. They'll have everything we've covered, so you won't need to repeat it.")]),
        (demo[2], "human_request", "P2", "L1 Service Desk", "Account disabled", 6, [
            ("user", "my account got disabled after I came back from leave"),
            ("ai", "I can't reactivate disabled accounts, so I'm connecting you to a technician with the details.")]),
        (demo[3], "mfa_no_prompt", "P2", "L2 Identity & Access", "MFA reset, lost phone", 9, [
            ("user", "nawala phone ko, di ako makakuha ng MFA prompt"),
            ("ai", "MFA registration has to be reset by a technician after identity checks. I'm connecting you now.")]),
        (demo[4], "softphone_audio", "P3", "Telephony Support", "One-way audio, fix failed twice", 14, [
            ("user", "one-way audio pa rin sa softphone"),
            ("ai", "Here are the SOP steps: select the headset for both speaker and microphone, check mute, allow microphone access, sign in again."),
            ("user", "ginawa ko na dalawang beses, wala pa rin"),
            ("ai", "Thanks for trying that. I'm passing this to the Telephony team with the steps already tried.")]),
    ]
    for emp_, intent, prio, grp, summ, mins, thread in cases:
        n += 1
        tid = f"TKT-{n}"
        created = now - timedelta(minutes=mins)
        cat = {"device_lost": "Hardware", "human_request": "Accounts", "mfa_no_prompt": "Accounts", "softphone_audio": "Telephony"}[intent]
        t = Ticket(ticket_id=tid, employee_id=emp_.employee_id, summary=summ, category=cat, priority=prio, status="Escalated",
                   assigned_group=grp, created_at=created, external_ref=f"ITSD-{rnd.randint(1000, 9999)}")
        db.add(t)
        cid = uuid.uuid4().hex[:16]
        db.add(Conversation(conversation_id=cid, employee_id=emp_.employee_id, ticket_id=tid, intent=intent, route="Escalate",
                            state={}, human_active=True, started_at=created))
        db.flush()
        for k, (who, txt) in enumerate(thread):
            db.add(Message(conversation_id=cid, sender=who, content_redacted=txt.replace("ticket and", f"ticket {tid} and"),
                           latency_ms=1800 if who == "ai" else None, created_at=created + timedelta(seconds=20 * k)))
        steps = {"device_lost": [], "softphone_audio": ["Shared the softphone audio SOP.", "Agent tried it twice without success."]}.get(intent, ["Ridley could not resolve this and connected a technician."])
        summary = build_summary(emp_, intent, summ, [], "Seeded example for the technician desk.", steps, prio)
        summary["suggested_reply"] = summary["suggested_reply"].replace("your ticket", tid)
        db.add(Escalation(conversation_id=cid, ticket_id=tid, status="Waiting", summary=summary, external_ref=t.external_ref, created_at=created))
    db.commit()
    rag.index_all(db)
