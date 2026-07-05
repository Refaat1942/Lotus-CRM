"""In-app alerts for complaints needing agent action."""
from datetime import datetime, timedelta

from sqlalchemy.exc import OperationalError, ProgrammingError

from app.extensions import db
from app.models import AppSetting, Complaint
from app.services.complaints import complaint_display_number, my_complaints_filter
from app.services.i18n import translate_status, translate_urgency

from app.services.urgency import URGENCY_IMMEDIATE

OPEN_STATUSES = ("مفتوحة", "جاري الحل")


def _stale_hours():
    try:
        return int(AppSetting.get("notify_stale_hours", "24") or "24")
    except ValueError:
        return 24


def _notify_immediate_enabled():
    return AppSetting.get("notify_immediate", "1") != "0"


def _notify_assigned_only(user):
    return AppSetting.get("notify_assigned_only", "0") == "1"


def _empty_notifications():
    return {
        "count": 0,
        "my_open": 0,
        "alerts": [],
        "criteria": {
            "stale_hours": _stale_hours(),
            "immediate": _notify_immediate_enabled(),
            "assigned_only": False,
        },
    }


def build_notifications(user, lang="ar"):
    try:
        return _build_notifications(user, lang)
    except (ProgrammingError, OperationalError):
        db.session.rollback()
        return _empty_notifications()


def _build_notifications(user, lang="ar"):
    now = datetime.now()
    stale_cutoff = now - timedelta(hours=_stale_hours())
    alerts = []

    base = Complaint.query.filter(Complaint.complaint_status.in_(OPEN_STATUSES))
    if _notify_assigned_only(user):
        base = base.filter(my_complaints_filter(user))

    immediate_rows = []
    if _notify_immediate_enabled():
        immediate_rows = base.filter(Complaint.urgency == URGENCY_IMMEDIATE).order_by(
            Complaint.complaint_date.desc()
        ).limit(20).all()

    stale_rows = base.filter(Complaint.complaint_date <= stale_cutoff).order_by(
        Complaint.complaint_date.asc()
    ).limit(20).all()

    unassigned = Complaint.query.filter(
        Complaint.complaint_status.in_(OPEN_STATUSES),
        Complaint.assigned_to_code.is_(None),
    ).order_by(Complaint.complaint_date.desc()).limit(15).all()

    seen_ids = set()

    def _add(row, kind, message_key, extra=""):
        if row.complaint_id in seen_ids:
            return
        seen_ids.add(row.complaint_id)
        alerts.append(
            {
                "id": row.complaint_id,
                "serial": complaint_display_number(row),
                "kind": kind,
                "message_key": message_key,
                "extra": extra,
                "status": row.complaint_status,
                "status_label": translate_status(row.complaint_status, lang),
                "urgency": row.urgency or "متوسطة",
                "urgency_label": translate_urgency(row.urgency or "متوسطة", lang),
                "assigned": row.assigned_to_name or "",
                "date": row.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "url": f"/complaints/{row.complaint_id}",
            }
        )

    for row in immediate_rows:
        _add(row, "urgent", "notif_immediate")

    for row in stale_rows:
        hours = int((now - row.complaint_date).total_seconds() // 3600)
        _add(row, "stale", "notif_stale", str(hours))

    for row in unassigned:
        if row.complaint_id not in seen_ids:
            _add(row, "unassigned", "notif_unassigned")

    my_open = Complaint.query.filter(
        my_complaints_filter(user),
        Complaint.complaint_status.in_(OPEN_STATUSES),
    ).count()

    return {
        "count": len(alerts),
        "my_open": my_open,
        "alerts": alerts[:30],
        "criteria": {
            "stale_hours": _stale_hours(),
            "immediate": _notify_immediate_enabled(),
            "assigned_only": _notify_assigned_only(user),
        },
    }
