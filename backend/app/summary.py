import json

from .config import settings
from .models import Employee

REPLIES = {
    "device_lost": "Hi {first}, this is {tech} from the Service Desk. Information Security has been notified and will lock and wipe your laptop remotely so your data stays safe. "
                   "Please tell your team lead and upload the police report to {ticket} within 48 hours. Your team lead will arrange a temporary workstation for your shift.",
    "phishing_report": "Hi {first}, thanks for reporting this. Please do not click anything in the email. Information Security will review it. "
                       "If you already clicked a link or typed your password, tell me now so we can secure your account.",
    "human_request": "Hi {first}, this is {tech} from the Service Desk. I have read the chat with Ridley, so you do not need to repeat anything. Let me look into this now.",
    "default": "Hi {first}, this is {tech} from the Service Desk. I have the full chat and the steps Ridley already tried, so you do not need to repeat them. I am checking this now and will update {ticket}.",
}

GROUP_FOR = {
    "device_lost": "Information Security", "phishing_report": "Information Security",
    "access_request": "L2 Identity & Access", "headset_issue": "IT Asset Management",
    "softphone_audio": "Telephony Support", "call_drops": "Telephony Support",
    "vpn_issue": "Network Support", "wfh_internet": "Network Support", "citrix_slow": "Citrix / VDI Support",
}


def build_summary(emp: Employee, intent: str, first_message: str, chunks: list, reason: str, steps: list, priority: str):
    group = GROUP_FOR.get(intent, "L1 Service Desk")
    data = [f"{emp.employee_id} on {emp.account.name if emp.account else 'no account'}, {emp.work_mode.lower()} at {emp.site}"]
    if emp.laptop:
        data.append(f"{emp.laptop} assigned to {emp.employee_id}")
    data.append("AD account: Locked" if emp.ad_locked else "AD account: Active")
    sources = [c["kb_id"] for c in chunks][:3]
    if intent == "device_lost":
        steps = ["None. P1 policy: no troubleshooting, escalate immediately."]
        data.append("Remote lock and wipe: requested")
        sources = ["KB-HW-003", "KB-014"]
    summary = {
        "issue": f"{emp.full_name} reports: {first_message[:160]}",
        "reason": reason,
        "steps_tried": steps or ["Ridley searched the knowledge base and found no approved fix."],
        "data_checked": data,
        "recommended_group": group,
        "priority": priority,
        "sources": sources,
        "suggested_reply": "",
    }
    summary["suggested_reply"] = suggested_reply(summary, intent, emp)
    return summary


def suggested_reply(summary: dict, intent: str, emp: Employee, tech: str = "your technician", ticket: str = "your ticket"):
    template = REPLIES.get(intent, REPLIES["default"])
    base = template.format(first=emp.full_name.split()[0], tech=tech, ticket=ticket)
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            res = client.chat.completions.create(
                model=settings.openai_model, temperature=0.3,
                messages=[
                    {"role": "system", "content": "Rewrite this IT Service Desk reply so it is warm, short and specific. Keep every fact. Return plain text only."},
                    {"role": "user", "content": json.dumps({"draft": base, "issue": summary["issue"]})},
                ],
            )
            return res.choices[0].message.content.strip()
        except Exception:
            pass
    return base
