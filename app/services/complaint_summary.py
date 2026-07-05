"""Rule-based complaint summaries for agents (no external AI)."""
from datetime import datetime

from app.services.complaint_categories import category_label_key
from app.services.complaints import complaint_display_number
from app.services.i18n import translate, translate_status, translate_urgency
from app.services.customer_data import full_name


def _age_label(complaint_date, lang):
    days = (datetime.now() - complaint_date).days
    if days <= 0:
        return "اليوم" if lang == "ar" else "today"
    if days == 1:
        return "أمس" if lang == "ar" else "yesterday"
    return f"منذ {days} يوم" if lang == "ar" else f"{days} days ago"


def _text_preview(text, limit=220):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def build_complaint_summary(complaint, customer_data=None, lang="ar"):
    """Return a short multi-line briefing for agents opening a complaint."""
    serial = complaint_display_number(complaint)
    status = translate_status(complaint.complaint_status, lang)
    urgency = translate_urgency(complaint.urgency or "متوسطة", lang)
    cat_key = complaint.complaint_category or "delivery"
    category = translate(category_label_key(cat_key), lang)
    branch = complaint.branch.branch_name if complaint.branch else (complaint.branch_code or "—")
    assigned = complaint.assigned_to_name or ("غير مُسند" if lang == "ar" else "Unassigned")
    channel = complaint.channel_detail or complaint.online_channel or ""
    customer_name = full_name(customer_data) if customer_data else ("—" if lang == "ar" else "Unknown")
    phone = complaint.phone_number
    age = _age_label(complaint.complaint_date, lang)
    preview = _text_preview(complaint.complaint_text)

    type_part = complaint.complaint_type or "—"
    channel_part = f" · {channel}" if channel else ""

    if lang == "ar":
        lines = [
            f"📋 {serial} — {status} — أولوية {urgency}",
        ]
        if getattr(complaint, "is_escalated", False):
            lines.append("⚠️ مُصعّدة للإدارة العليا — تتطلب متابعة فورية")
        lines.extend(
            [
                f"👤 {customer_name} · {phone}",
                f"🏷 {category} / {type_part}{channel_part}",
                f"🏢 {branch} · مُسند: {assigned} · {age}",
                f"💬 {preview}",
            ]
        )
    else:
        lines = [
            f"📋 {serial} — {status} — {urgency} priority",
        ]
        if getattr(complaint, "is_escalated", False):
            lines.append("⚠️ Escalated to upper management — needs immediate attention")
        lines.extend(
            [
                f"👤 {customer_name} · {phone}",
                f"🏷 {category} / {type_part}{channel_part}",
                f"🏢 {branch} · Assigned: {assigned} · {age}",
                f"💬 {preview}",
            ]
        )
    return "\n".join(lines)
