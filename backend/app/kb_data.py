KB_ARTICLES = [
    {
        "kb_id": "KB-ACC-001", "version": "v1.0", "category": "Accounts & Access",
        "title": "Account Locked Due to Multiple Failed Login Attempts",
        "body": """## Summary
A Windows or Active Directory account locks after 5 failed sign-in attempts. It unlocks on its own after 30 minutes. An agent who cannot wait can have it unlocked after identity verification.
## Steps
1. Confirm the Employee ID and check the lock time.
2. Send a 6-digit verification code to the mobile number registered on the employee record.
3. Once the code is entered correctly, unlock the account.
4. Tell the agent to update the saved password on their phone or email app so the lockout does not repeat.
## Policy
Only the account owner can request an unlock. Technicians never unlock an account for another person over chat.""",
    },
    {
        "kb_id": "KB-ACC-002", "version": "v3.0", "category": "Accounts & Access",
        "title": "Password Reset and Account Lockout Policy",
        "body": """## Summary
Passwords expire every 90 days. A forgotten password can be reset by the owner after a one-time code is confirmed.
## Steps
1. Verify the owner with a 6-digit code sent to the registered mobile number.
2. Issue a temporary password that must be changed at the next sign-in.
3. Remind the agent that the new password needs 12 characters, with one number and one symbol.
## Policy
Passwords are never shared in chat. A reset for another employee must come from that employee or from the Service Desk.""",
    },
    {
        "kb_id": "KB-ACC-006", "version": "v1.0", "category": "Accounts & Access",
        "title": "MFA Prompt Not Received",
        "body": """## Summary
The MFA prompt does not arrive after a new phone, a changed number or poor signal.
## Steps
1. Check that the phone has signal or Wi-Fi and that notifications are on for the authenticator app.
2. Open the authenticator app and use the code shown there instead of waiting for the push.
3. If the phone was replaced or lost, the MFA registration must be reset by the Service Desk. Ridley raises the request and a technician completes it after checking identity.""",
    },
    {
        "kb_id": "KB-NET-001", "version": "v2.1", "category": "Network & Remote Access",
        "title": "TaskUs VPN Troubleshooting",
        "body": """## Common Error Codes
VPN-301 means the gateway cannot be reached. VPN-303 means the session timed out. VPN-309 means the certificate expired and the device must be re-enrolled.
## Steps
1. Close the VPN client completely and open it again.
2. Make sure the gateway is vpn-ph.taskus.local.
3. Restart the router, then test the home internet with another website.
4. For VPN-309, ask the Service Desk to re-enroll the device certificate.
## Escalate when
The error continues after a router restart and a second device on the same internet connection works.""",
    },
    {
        "kb_id": "KB-NET-002", "version": "v1.0", "category": "Network & Remote Access",
        "title": "VPN Gateway Address",
        "body": """## Policy and key facts
The correct gateway is vpn-ph.taskus.local. The old gateway vpn1.taskus.local was decommissioned on 2026-01-15 and must not be used.""",
    },
    {
        "kb_id": "KB-NET-003", "version": "v1.0", "category": "Network & Remote Access",
        "title": "VPN Session Timeout",
        "body": """## Policy and key facts
VPN sessions expire after 10 hours. Reconnect at the start of every shift so the session does not drop in the middle of a call.""",
    },
    {
        "kb_id": "KB-NET-004", "version": "v4.0", "category": "Network & Remote Access",
        "title": "Work-From-Home Technical Requirements",
        "body": """## Summary
Agents working from home need at least 15 Mbps download, 5 Mbps upload, latency under 80 ms and a wired or 5 GHz Wi-Fi connection.
## Steps
1. Run the speed test and note the numbers.
2. Move closer to the router or use a LAN cable.
3. Ask other people in the house to pause streaming and large downloads during the shift.
4. If the numbers stay below the minimum, tell the team lead so the shift can be moved on-site.""",
    },
    {
        "kb_id": "KB-TEL-001", "version": "v1.0", "category": "Telephony & Audio",
        "title": "Softphone One-Way or No Audio",
        "body": """## Steps
1. In the softphone settings, select the headset as both the speaker and the microphone.
2. Check that the headset is not muted by the in-line button.
3. Allow microphone access for the softphone in the Windows privacy settings.
4. Sign out of the softphone and sign in again.
5. Test with a test call before taking customer calls.
## Escalate when
The headset works on another computer but still has no audio on this one.""",
    },
    {
        "kb_id": "KB-TEL-003", "version": "v1.0", "category": "Telephony & Audio",
        "title": "Calls Dropping Every Few Minutes",
        "body": """## Summary
Frequent call drops usually come from weak Wi-Fi or a VPN session that keeps reconnecting.
## Steps
1. Switch from Wi-Fi to a LAN cable if possible.
2. Check that no one else is using the connection for downloads or video.
3. Reconnect the VPN and confirm the gateway is vpn-ph.taskus.local.
4. If the drops continue, note the time of the last three drops and escalate to the Telephony team.""",
    },
    {
        "kb_id": "KB-APP-002", "version": "v1.0", "category": "Applications",
        "title": "Citrix Session Slow or Frozen",
        "body": """## Summary
Slow or frozen Citrix sessions are common when many users share one site or the network is congested.
## Steps
1. Check the status banner. If there is an active Citrix incident, wait for the next update instead of filing another ticket.
2. Log off the Citrix session fully and sign in again.
3. Close unused browser tabs and large applications on the local computer.
4. If there is no active incident and the problem stays, a technician can reset the session. Ridley can reset it after identity is confirmed.""",
    },
    {
        "kb_id": "KB-APP-003", "version": "v1.0", "category": "Applications",
        "title": "Software and Application Access Requests",
        "body": """## Summary
Access to client tools such as the CRM needs approval from the team lead and an access ticket for the Identity and Access team.
## Steps
1. Ask for the application name and the reason.
2. Create an access request ticket for the Identity and Access team.
3. Tell the agent the request takes up to 3 business days and the team lead will be asked to approve.""",
    },
    {
        "kb_id": "KB-HW-001", "version": "v1.0", "category": "Hardware & Peripherals",
        "title": "Headset Microphone Not Working",
        "body": """## Steps
1. Unplug the headset and plug it into a different USB port.
2. Check the in-line mute switch.
3. In Windows sound settings, set the headset as the default input device.
4. If the headset still fails, a replacement is issued by IT Asset Management and the ticket is set to P3.""",
    },
    {
        "kb_id": "KB-HW-003", "version": "v1.0", "category": "Hardware & Peripherals",
        "title": "Lost or Stolen Laptop",
        "body": """## Policy and key facts
A lost or stolen company device is a P1 security incident. No troubleshooting is done in chat. The ticket goes straight to Information Security, who lock and wipe the laptop remotely. The agent must tell the team lead and file a police report within 48 hours.""",
    },
    {
        "kb_id": "KB-SEC-001", "version": "v1.0", "category": "Security",
        "title": "Phishing Email Reporting",
        "body": """## Steps
1. Do not click links or open attachments in the email.
2. Report the email with the report phishing button or forward it to the security mailbox.
3. If a link was clicked or a password was typed, the agent must tell Information Security right away so the account can be secured.
## Policy
Reported phishing emails are reviewed by Information Security, so Ridley escalates every report.""",
    },
    {
        "kb_id": "KB-014", "version": "v3.0", "category": "Service Management",
        "title": "IT Escalation Matrix and Priority Definitions",
        "body": """## Priority and SLA
P1 is critical: security incident or site down, acknowledged within 15 minutes, resolved within 4 hours. P2 is high, resolved within 8 hours. P3 is medium, resolved within 2 business days. P4 is low, resolved within 5 business days.
## Groups
Accounts and password issues go to the AI Helpdesk or L1 Service Desk. Access requests go to L2 Identity and Access. Hardware goes to IT Asset Management. Telephony goes to the Telephony team. Security incidents go to Information Security.""",
    },
    {
        "kb_id": "KB-015", "version": "v2026.10", "category": "Service Management",
        "title": "Planned Maintenance Calendar and Known Issues",
        "body": """## Known issues
Citrix at Site 2 is degraded and tracked as INC-2026-1187. No separate ticket is needed. Updates are posted on the banner.""",
    },
    {
        "kb_id": "KB-002", "version": "v1.0", "category": "Network & Remote Access",
        "title": "TaskUs VPN Troubleshooting (v1)", "status": "superseded",
        "body": """## Common Error Codes
Sessions expire every 8 hours. The gateway is vpn1.taskus.local. Restart the client when VPN-301 appears.""",
    },
]
