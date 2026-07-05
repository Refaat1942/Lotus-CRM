"""Live CRM activity feed for admin monitoring screen."""
from datetime import datetime, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import AuditLog, Complaint, ComplaintDetail, User
from app.services.complaints import complaint_display_number
from app.services.i18n import translate_status, translate_urgency
from app.services.urgency import URGENCY_IMMEDIATE


def build_live_feed(lang="ar", limit=40):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    today_count = Complaint.query.filter(Complaint.complaint_date >= today_start).count()
    open_count = Complaint.query.filter(Complaint.complaint_status.in_(("مفتوحة", "جاري الحل"))).count()
    immediate_count = Complaint.query.filter(
        Complaint.complaint_status.in_(("مفتوحة", "جاري الحل")),
        Complaint.urgency == URGENCY_IMMEDIATE,
    ).count()
    unassigned = Complaint.query.filter(
        Complaint.complaint_status.in_(("مفتوحة", "جاري الحل")),
        Complaint.assigned_to_code.is_(None),
    ).count()
    active_users = (
        AuditLog.query.filter(
            AuditLog.action == "user.login",
            AuditLog.created_at >= hour_ago,
        )
        .with_entities(AuditLog.username)
        .distinct()
        .count()
    )

    recent_complaints = Complaint.query.order_by(Complaint.complaint_date.desc()).limit(15).all()
    complaints_feed = [
        {
            "serial": complaint_display_number(c),
            "phone": c.phone_number,
            "agent": c.assigned_to_name or c.created_by_name or "—",
            "status_label": translate_status(c.complaint_status, lang),
            "urgency_label": translate_urgency(c.urgency or "متوسطة", lang),
            "branch": c.branch.branch_name if c.branch else c.branch_code,
            "time": c.complaint_date.strftime("%H:%M:%S"),
            "url": f"/complaints/{c.complaint_id}",
        }
        for c in recent_complaints
    ]

    audit_rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    activity_feed = [
        {
            "time": r.created_at.strftime("%H:%M:%S"),
            "user": r.username or "—",
            "action": r.action,
            "details": (r.details or "")[:120],
            "entity": f"{r.entity_type or ''} {r.entity_id or ''}".strip(),
        }
        for r in audit_rows
    ]

    timeline_rows = (
        ComplaintDetail.query.order_by(ComplaintDetail.detail_date.desc()).limit(20).all()
    )
    updates_feed = [
        {
            "time": d.detail_date.strftime("%H:%M:%S"),
            "user": d.modifier or "—",
            "text": (d.detail_text or "")[:100],
            "type": d.action_type or "note",
            "complaint_id": d.complaint_id,
        }
        for d in timeline_rows
    ]

    by_agent = (
        db.session.query(Complaint.assigned_to_name, func.count(Complaint.complaint_id))
        .filter(Complaint.complaint_date >= today_start, Complaint.assigned_to_name.isnot(None))
        .group_by(Complaint.assigned_to_name)
        .order_by(func.count(Complaint.complaint_id).desc())
        .limit(10)
        .all()
    )

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "today": today_count,
            "open": open_count,
            "immediate": immediate_count,
            "unassigned": unassigned,
            "active_users": active_users,
            "total_users": User.query.filter_by(is_active=True).count(),
        },
        "agent_today": [{"name": n or "—", "count": c} for n, c in by_agent],
        "complaints": complaints_feed,
        "activity": activity_feed,
        "updates": updates_feed,
    }
