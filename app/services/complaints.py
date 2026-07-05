"""Complaint serial numbers, filters, and dashboard aggregates."""
from datetime import datetime, timedelta

from sqlalchemy import func, or_

from app.extensions import db
from app.models import Branch, Complaint, ComplaintType, Customer, Employee
from app.services.i18n import translate_complaint_type, translate_status

SERIAL_PREFIX = "CMP"


def complaint_display_number(complaint):
    if complaint.serial_number:
        return complaint.serial_number
    return f"#{complaint.complaint_id}"


def generate_complaint_serial(branch_code, when=None):
    """Daily per-branch serial: {BRANCH}-YYYYMMDD-0001, {BRANCH}-YYYYMMDD-0002, …"""
    when = when or datetime.now()
    branch_code = (branch_code or "GEN").strip().upper().replace(" ", "")[:15]
    date_str = when.strftime("%Y%m%d")
    prefix = f"{branch_code}-{date_str}-"
    day_start = when.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = when.replace(hour=23, minute=59, second=59, microsecond=999999)

    for _ in range(10):
        last = (
            Complaint.query.filter(
                Complaint.branch_code == branch_code,
                Complaint.complaint_date >= day_start,
                Complaint.complaint_date <= day_end,
                Complaint.serial_number.like(f"{prefix}%"),
            )
            .order_by(Complaint.serial_number.desc())
            .first()
        )
        if last and last.serial_number:
            try:
                seq = int(last.serial_number.rsplit("-", 1)[-1]) + 1
            except ValueError:
                seq = 1
        else:
            seq = 1
        serial = f"{prefix}{seq:04d}"
        if not Complaint.query.filter_by(serial_number=serial).first():
            return serial
    raise RuntimeError("Could not generate unique complaint serial")


OPEN_STATUSES = ("مفتوحة", "جاري الحل")
CLOSED_STATUS = "مغلقة"


def _stale_hours_setting():
    from app.models import AppSetting

    try:
        return int(AppSetting.get("notify_stale_hours", "24") or "24")
    except ValueError:
        return 24


def follow_up_kind(complaint, now=None):
    """Return follow-up reason key for open complaints, or None if closed."""
    if complaint.complaint_status not in OPEN_STATUSES:
        return None
    now = now or datetime.now()
    from app.services.urgency import URGENCY_IMMEDIATE

    if complaint.urgency == URGENCY_IMMEDIATE:
        return "immediate"
    if complaint.is_escalated:
        return "escalated"
    stale_hours = _stale_hours_setting()
    if (now - complaint.complaint_date).total_seconds() >= stale_hours * 3600:
        return "stale"
    if complaint.complaint_status == "مفتوحة":
        return "open"
    return "in_progress"


def _agent_employee(user):
    emp = user.employee if getattr(user, "employee", None) else None
    if not emp and user.employee_code:
        emp = Employee.query.get(user.employee_code)
    return emp


def _complaint_is_mine(complaint, user, emp=None):
    emp = emp or _agent_employee(user)
    if emp:
        if complaint.assigned_to_code == emp.employee_code:
            return True
        if not complaint.assigned_to_code and complaint.created_by_code == emp.employee_code:
            return True
        return False
    name = user.username
    if complaint.assigned_to_name == name:
        return True
    if not complaint.assigned_to_name and complaint.created_by_name == name:
        return True
    return False


def build_agent_complaints_board(user, lang="ar", status_filter="all"):
    """All complaints with status and follow-up flags (highlight current agent's rows)."""
    from app.services.i18n import translate_complaint_type, translate_status, translate_urgency
    from app.models import ComplaintType

    type_map = {t.name_ar: t.display_name(lang) for t in ComplaintType.query.all()}
    emp = _agent_employee(user)

    q = Complaint.query
    if status_filter == "open":
        q = q.filter(Complaint.complaint_status.in_(OPEN_STATUSES))
    elif status_filter == "closed":
        q = q.filter(Complaint.complaint_status == CLOSED_STATUS)
    elif status_filter == "followup":
        q = q.filter(Complaint.complaint_status.in_(OPEN_STATUSES))

    rows = q.order_by(Complaint.complaint_date.desc()).limit(500).all()
    now = datetime.now()
    items = []
    for c in rows:
        kind = follow_up_kind(c, now)
        if status_filter == "followup" and not kind:
            continue
        items.append(
            {
                "id": c.complaint_id,
                "serial": complaint_display_number(c),
                "phone": c.phone_number,
                "type": c.complaint_type,
                "type_label": type_map.get(
                    c.complaint_type,
                    translate_complaint_type(c.complaint_type, lang) if c.complaint_type else "—",
                ),
                "status": c.complaint_status,
                "status_label": translate_status(c.complaint_status, lang),
                "urgency": c.urgency or "متوسطة",
                "urgency_label": translate_urgency(c.urgency or "متوسطة", lang),
                "branch": c.branch.branch_name if c.branch else c.branch_code,
                "date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "assigned": c.assigned_to_name or "—",
                "is_mine": _complaint_is_mine(c, user, emp),
                "escalated": bool(c.is_escalated),
                "follow_up": kind,
                "follow_up_label_key": f"follow_up_{kind}" if kind else None,
                "url": f"/complaints/{c.complaint_id}",
            }
        )

    items.sort(key=lambda x: x["date"], reverse=True)
    items.sort(key=lambda x: 0 if x["follow_up"] else 1)
    open_count = sum(1 for i in items if i["status"] in OPEN_STATUSES)
    followup_count = sum(1 for i in items if i["follow_up"])
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "open": open_count,
            "followup": followup_count,
            "closed": sum(1 for i in items if i["status"] == CLOSED_STATUS),
        },
    }


def my_complaints_filter(user):
    emp = _agent_employee(user)
    if emp:
        return or_(
            Complaint.assigned_to_code == emp.employee_code,
            (
                Complaint.assigned_to_code.is_(None)
                & (Complaint.created_by_code == emp.employee_code)
            ),
        )
    name = user.username
    return or_(
        Complaint.assigned_to_name == name,
        (Complaint.assigned_to_name.is_(None) & (Complaint.created_by_name == name)),
    )


def _parse_date(value, end_of_day=False):
    if not value:
        return None
    dt = datetime.strptime(value, "%Y-%m-%d")
    if end_of_day:
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


def _filtered_complaints(date_from, date_to, branch="الكل", status="الكل"):
    q = Complaint.query
    start = _parse_date(date_from)
    end = _parse_date(date_to, end_of_day=True)
    if start:
        q = q.filter(Complaint.complaint_date >= start)
    if end:
        q = q.filter(Complaint.complaint_date <= end)
    if branch and branch not in ("الكل", "all", ""):
        q = q.filter(Complaint.branch_code == branch)
    if status and status not in ("الكل", "all", ""):
        q = q.filter(Complaint.complaint_status == status)
    return q


def _complaint_filters(date_from, date_to, branch="الكل", status="الكل"):
    """Return filter clauses reusable in aggregate queries."""
    clauses = []
    start = _parse_date(date_from)
    end = _parse_date(date_to, end_of_day=True)
    if start:
        clauses.append(Complaint.complaint_date >= start)
    if end:
        clauses.append(Complaint.complaint_date <= end)
    if branch and branch not in ("الكل", "all", ""):
        clauses.append(Complaint.branch_code == branch)
    if status and status not in ("الكل", "all", ""):
        clauses.append(Complaint.complaint_status == status)
    return clauses


def build_dashboard_overview(date_from, date_to, branch="الكل", status="الكل", lang="ar"):
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    base = _filtered_complaints(date_from, date_to, branch, status)
    filters = _complaint_filters(date_from, date_to, branch, status)
    total = base.count()

    today_q = Complaint.query.filter(
        Complaint.complaint_date >= today_start,
        Complaint.complaint_date <= today_end,
    )
    if branch and branch not in ("الكل", "all", ""):
        today_q = today_q.filter(Complaint.branch_code == branch)
    created_today = today_q.count()

    open_count = base.filter(Complaint.complaint_status == "مفتوحة").count()
    in_progress = base.filter(Complaint.complaint_status == "جاري الحل").count()
    closed_count = base.filter(Complaint.complaint_status == "مغلقة").count()

    by_status = (
        db.session.query(Complaint.complaint_status, func.count(Complaint.complaint_id))
        .filter(*filters)
        .group_by(Complaint.complaint_status)
        .all()
    )
    status_rows = [
        {
            "status": row[0],
            "status_label": translate_status(row[0], lang),
            "count": row[1],
        }
        for row in by_status
    ]

    start = _parse_date(date_from) or today_start
    end = _parse_date(date_to, end_of_day=True) or today_end
    if end < start:
        start, end = end, start

    day_counts = (
        db.session.query(func.date(Complaint.complaint_date), func.count(Complaint.complaint_id))
        .filter(*filters)
        .group_by(func.date(Complaint.complaint_date))
        .order_by(func.date(Complaint.complaint_date))
        .all()
    )
    count_map = {str(d): c for d, c in day_counts}

    by_day = []
    cursor = start.date()
    end_date = end.date()
    while cursor <= end_date:
        key = cursor.isoformat()
        by_day.append({"date": key, "count": count_map.get(key, 0)})
        cursor += timedelta(days=1)

    type_map = {t.name_ar: t.display_name(lang) for t in ComplaintType.query.all()}
    by_type_raw = (
        db.session.query(Complaint.complaint_type, func.count(Complaint.complaint_id))
        .filter(*filters)
        .group_by(Complaint.complaint_type)
        .order_by(func.count(Complaint.complaint_id).desc())
        .limit(8)
        .all()
    )
    by_type = [
        {
            "type": row[0],
            "type_label": type_map.get(row[0], translate_complaint_type(row[0], lang)),
            "count": row[1],
        }
        for row in by_type_raw
    ]

    by_branch_raw = (
        db.session.query(Branch.branch_name, func.count(Complaint.complaint_id))
        .join(Complaint, Complaint.branch_code == Branch.branch_code)
        .filter(*filters)
        .group_by(Branch.branch_name)
        .order_by(func.count(Complaint.complaint_id).desc())
        .limit(8)
        .all()
    )
    by_branch = [{"branch": row[0], "count": row[1]} for row in by_branch_raw]

    recent = base.order_by(Complaint.complaint_date.desc()).limit(10).all()
    recent_rows = []
    for c in recent:
        cust = Customer.query.filter_by(phone_number=c.phone_number).first()
        cust_name = f"{cust.first_name or ''} {cust.last_name or ''}".strip() if cust else ""
        recent_rows.append(
            {
                "id": c.complaint_id,
                "serial": complaint_display_number(c),
                "phone": c.phone_number,
                "customer": cust_name,
                "status": c.complaint_status,
                "status_label": translate_status(c.complaint_status, lang),
                "date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "branch": c.branch.branch_name if c.branch else c.branch_code,
            }
        )

    return {
        "summary": {
            "total": total,
            "created_today": created_today,
            "open": open_count,
            "in_progress": in_progress,
            "closed": closed_count,
        },
        "by_status": status_rows,
        "by_day": by_day,
        "by_type": by_type,
        "by_branch": by_branch,
        "recent": recent_rows,
    }
