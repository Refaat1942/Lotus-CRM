import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import msal
import requests

from app.models import AppSetting, Branch


def send_escalation_notification(branch_code, serial, details):
    """Notify upper management (area / sales / owner) about an escalated complaint."""
    use_graph = AppSetting.get("use_graph_api", "0") == "1"
    if use_graph:
        return _send_escalation_via_graph(branch_code, serial, details)
    return _send_escalation_via_smtp(branch_code, serial, details)


def get_escalation_recipient_emails(branch_code):
    """Emails notified when a complaint is escalated (upper management)."""
    branch = Branch.query.get(branch_code)
    if not branch:
        return []
    return [
        e
        for e in [
            branch.area_manager_email,
            branch.sales_manager_email,
            branch.owner_email,
        ]
        if e
    ]


def get_escalation_recipient_rows(branch_code, lang="ar"):
    """Labeled escalation recipients for display in the UI."""
    branch = Branch.query.get(branch_code)
    if not branch:
        return []
    from app.services.i18n import translate

    mapping = [
        ("area_manager_email", branch.area_manager_email),
        ("sales_manager_email", branch.sales_manager_email),
        ("owner_email", branch.owner_email),
    ]
    rows = []
    for key, email in mapping:
        if email:
            rows.append({"label": translate(key, lang), "email": email})
    return rows


def _get_upper_management_emails(branch_code):
    return get_escalation_recipient_emails(branch_code)


def _send_escalation_via_smtp(branch_code, serial, details):
    to_addrs = _get_upper_management_emails(branch_code)
    if not to_addrs:
        return False

    host = AppSetting.get("smtp_host", "")
    port = int(AppSetting.get("smtp_port", "587") or "587")
    user = AppSetting.get("smtp_user", "")
    password = AppSetting.get("smtp_password", "")
    from_addr = AppSetting.get("notification_email", user)

    if not host or not from_addr:
        raise RuntimeError("SMTP not configured. Set email settings in Admin panel.")

    subject = f"ESCALATION — Complaint {serial} at branch {branch_code}"
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(details, "plain"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, to_addrs, msg.as_string())
    return True


def _send_escalation_via_graph(branch_code, serial, details):
    tenant_id = AppSetting.get("graph_tenant_id", "")
    client_id = AppSetting.get("graph_client_id", "")
    client_secret = AppSetting.get("graph_client_secret", "")
    from_addr = AppSetting.get("notification_email", "")

    if not all([tenant_id, client_id, client_secret, from_addr]):
        raise RuntimeError("Microsoft Graph not fully configured.")

    to_addrs = _get_upper_management_emails(branch_code)
    if not to_addrs:
        return False

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in token:
        raise RuntimeError(token.get("error_description", "Graph auth failed"))

    payload = {
        "message": {
            "subject": f"ESCALATION — Complaint {serial} at branch {branch_code}",
            "body": {"contentType": "Text", "content": details},
            "toRecipients": [{"emailAddress": {"address": a}} for a in to_addrs],
        },
        "saveToSentItems": "true",
    }
    url = f"https://graph.microsoft.com/v1.0/users/{from_addr}/sendMail"
    resp = requests.post(
        url,
        headers={
            "Authorization": "Bearer " + token["access_token"],
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Graph sendMail failed: {resp.status_code} – {resp.text}")
    return True


def send_complaint_notification(branch_code, details):
    """Send complaint notification using configured method (SMTP or Graph)."""
    use_graph = AppSetting.get("use_graph_api", "0") == "1"
    if use_graph:
        return _send_via_graph(branch_code, details)
    return _send_via_smtp(branch_code, details)


def _get_branch_emails(branch_code):
    branch = Branch.query.get(branch_code)
    if not branch:
        return [], []
    to_addrs = [e for e in [branch.branch_manager_email] if e]
    cc_addrs = [e for e in [branch.area_manager_email, branch.sales_manager_email, branch.owner_email] if e]
    return to_addrs, cc_addrs


def _send_via_smtp(branch_code, details):
    to_addrs, cc_addrs = _get_branch_emails(branch_code)
    if not to_addrs:
        return False

    host = AppSetting.get("smtp_host", "")
    port = int(AppSetting.get("smtp_port", "587") or "587")
    user = AppSetting.get("smtp_user", "")
    password = AppSetting.get("smtp_password", "")
    from_addr = AppSetting.get("notification_email", user)

    if not host or not from_addr:
        raise RuntimeError("SMTP not configured. Set email settings in Admin panel.")

    subject = f"New complaint at branch {branch_code}"
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(details, "plain"))

    all_recipients = to_addrs + cc_addrs
    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_addr, all_recipients, msg.as_string())
    return True


def _send_via_graph(branch_code, details):
    tenant_id = AppSetting.get("graph_tenant_id", "")
    client_id = AppSetting.get("graph_client_id", "")
    client_secret = AppSetting.get("graph_client_secret", "")
    from_addr = AppSetting.get("notification_email", "")

    if not all([tenant_id, client_id, client_secret, from_addr]):
        raise RuntimeError("Microsoft Graph not fully configured.")

    to_addrs, cc_addrs = _get_branch_emails(branch_code)
    if not to_addrs:
        return False

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id=client_id,
        authority=authority,
        client_credential=client_secret,
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in token:
        raise RuntimeError(token.get("error_description", "Graph auth failed"))

    payload = {
        "message": {
            "subject": f"New complaint at branch {branch_code}",
            "body": {"contentType": "Text", "content": details},
            "toRecipients": [{"emailAddress": {"address": a}} for a in to_addrs],
            "ccRecipients": [{"emailAddress": {"address": a}} for a in cc_addrs],
        },
        "saveToSentItems": "true",
    }
    url = f"https://graph.microsoft.com/v1.0/users/{from_addr}/sendMail"
    resp = requests.post(
        url,
        headers={
            "Authorization": "Bearer " + token["access_token"],
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(f"Graph sendMail failed: {resp.status_code} – {resp.text}")
    return True
