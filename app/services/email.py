import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import msal
import requests

from app.models import AppSetting, Branch


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
