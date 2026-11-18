from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.utcnow()


class ClientAccount(Base):
    __tablename__ = "client_accounts"
    account_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    sla_minutes: Mapped[int] = mapped_column(Integer, default=240)


class Employee(Base):
    __tablename__ = "employees"
    employee_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("client_accounts.account_id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="agent")
    title: Mapped[str] = mapped_column(String(80), default="Agent")
    site: Mapped[str] = mapped_column(String(40), default="Site 2")
    work_mode: Mapped[str] = mapped_column(String(20), default="On-site")
    password_hash: Mapped[str] = mapped_column(String(200))
    mobile_hash: Mapped[str] = mapped_column(String(80), default="")
    mobile_last4: Mapped[str] = mapped_column(String(4), default="0000")
    laptop: Mapped[str] = mapped_column(String(20), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    ad_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    ad_locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    account = relationship("ClientAccount")


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"), index=True)
    summary: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(4), default="P3")
    status: Mapped[str] = mapped_column(String(20), default="Open", index=True)
    assigned_group: Mapped[str] = mapped_column(String(60), default="L1 Service Desk")
    resolved_by: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)
    employee = relationship("Employee")


class Conversation(Base):
    __tablename__ = "conversations"
    conversation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"), index=True)
    ticket_id: Mapped[str | None] = mapped_column(ForeignKey("tickets.ticket_id"), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    route: Mapped[str | None] = mapped_column(String(20), nullable=True)
    csat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    human_active: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    employee = relationship("Employee")


class Message(Base):
    __tablename__ = "messages"
    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.conversation_id"), index=True)
    sender: Mapped[str] = mapped_column(String(10))
    content_redacted: Mapped[str] = mapped_column(Text, default="")
    blocks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    kb_article_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Escalation(Base):
    __tablename__ = "escalations"
    escalation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.conversation_id"), index=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"))
    technician_id: Mapped[str | None] = mapped_column(ForeignKey("employees.employee_id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Waiting")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    external_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    taken_over_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conversation = relationship("Conversation")
    ticket = relationship("Ticket")


class KBArticle(Base):
    __tablename__ = "kb_articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kb_id: Mapped[str] = mapped_column(String(30), index=True)
    version: Mapped[str] = mapped_column(String(12), default="v1.0")
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="active")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class FunctionCall(Base):
    __tablename__ = "function_calls"
    call_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(20))
    function_name: Mapped[str] = mapped_column(String(40))
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[str] = mapped_column(String(200), default="")
    called_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class GuardrailEvent(Base):
    __tablename__ = "guardrail_events"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(60))
    detail: Mapped[str] = mapped_column(String(240))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    otp_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[str] = mapped_column(String(20), index=True)
    purpose: Mapped[str] = mapped_column(String(40))
    code_hash: Mapped[str] = mapped_column(String(80))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Incident(Base):
    __tablename__ = "incidents"
    incident_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    site: Mapped[str] = mapped_column(String(40))
    next_update: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
