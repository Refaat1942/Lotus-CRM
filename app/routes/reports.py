import io
from datetime import datetime

from flask import Blueprint, render_template, request, send_file, session
from flask_login import current_user, login_required
from openpyxl import Workbook
from sqlalchemy import func

from app.decorators import feature_required, permission_required
from app.extensions import db
from app.models import AuditLog, Branch, Complaint, Customer, User
from app.services.complaints import complaint_display_number
from app.services.i18n import translate_status, translate_urgency

reports_bp = Blueprint("reports", __name__)

STATUSES = ["مفتوحة", "جاري الحل", "مغلقة"]
URGENCIES = ["ضعيفة", "متوسطة", "فورية"]


def _rows_to_excel(data):
    wb = Workbook()
    ws = wb.active
    if not data:
        ws.append(["No data"])
    else:
        headers = list(data[0].keys())
        ws.append(headers)
        for row in data:
            ws.append([row.get(h) for h in headers])
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _parse_dates():
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    start = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    end = (
        datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        if date_to
        else None
    )
    return start, end


def _complaint_filters():
    clauses = []
    start, end = _parse_dates()
    if start:
        clauses.append(Complaint.complaint_date >= start)
    if end:
        clauses.append(Complaint.complaint_date <= end)
    branch = request.args.get("branch", "الكل")
    status = request.args.get("status", "الكل")
    urgency = request.args.get("urgency", "الكل")
    agent = request.args.get("agent", "").strip()
    if branch and branch not in ("الكل", "all", ""):
        clauses.append(Complaint.branch_code == branch)
    if status and status not in ("الكل", "all", ""):
        clauses.append(Complaint.complaint_status == status)
    if urgency and urgency not in ("الكل", "all", ""):
        clauses.append(Complaint.urgency == urgency)
    if agent:
        clauses.append(Complaint.assigned_to_name.contains(agent))
    return clauses


def _complaint_query():
    return Complaint.query.filter(*_complaint_filters())


def _export_if_requested(data, name):
    if request.args.get("export") == "excel" and current_user.permissions.can_export_excel:
        return send_file(
            _rows_to_excel(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"{name}_{datetime.now():%Y%m%d}.xlsx",
        )
    return None


def _report_context(extra=None):
    ctx = {
        "branches": Branch.query.order_by(Branch.branch_name).all(),
        "statuses": STATUSES,
        "urgencies": URGENCIES,
    }
    if extra:
        ctx.update(extra)
    return ctx


@reports_bp.route("/")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def index():
    return render_template("reports/index.html")


@reports_bp.route("/complaints")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def complaints_report():
    lang = session.get("lang", "ar")
    rows = _complaint_query().order_by(Complaint.complaint_date.desc()).all()
    data = [
        {
            "Serial": complaint_display_number(c),
            "Phone": c.phone_number,
            "Type": c.complaint_type,
            "Status": translate_status(c.complaint_status, lang),
            "Urgency": translate_urgency(c.urgency or "متوسطة", lang),
            "Agent": c.assigned_to_name or c.created_by_name or "",
            "Date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
            "Branch": c.branch.branch_name if c.branch else c.branch_code,
            "Text": (c.complaint_text or "")[:200],
        }
        for c in rows
    ]
    resp = _export_if_requested(data, "complaints")
    if resp:
        return resp
    return render_template("reports/complaints.html", rows=data, **_report_context())


@reports_bp.route("/agents")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def agents_report():
    start, end = _parse_dates()
    q = db.session.query(
        Complaint.assigned_to_name,
        Complaint.complaint_status,
        func.count(Complaint.complaint_id),
    )
    if start:
        q = q.filter(Complaint.complaint_date >= start)
    if end:
        q = q.filter(Complaint.complaint_date <= end)
    q = q.filter(Complaint.assigned_to_name.isnot(None))
    q = q.group_by(Complaint.assigned_to_name, Complaint.complaint_status)
    lang = session.get("lang", "ar")
    data = [
        {
            "Agent": r[0],
            "Status": translate_status(r[1], lang),
            "Count": r[2],
        }
        for r in q.order_by(func.count(Complaint.complaint_id).desc()).all()
    ]
    resp = _export_if_requested(data, "agents")
    if resp:
        return resp
    return render_template("reports/agents.html", rows=data, **_report_context())


@reports_bp.route("/audit")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def audit_report():
    start, end = _parse_dates()
    q = AuditLog.query
    if start:
        q = q.filter(AuditLog.created_at >= start)
    if end:
        q = q.filter(AuditLog.created_at <= end)
    user = request.args.get("user", "").strip()
    if user:
        q = q.filter(AuditLog.username.contains(user))
    rows = q.order_by(AuditLog.created_at.desc()).limit(500).all()
    data = [
        {
            "Time": r.created_at.strftime("%Y-%m-%d %H:%M"),
            "User": r.username or "",
            "Action": r.action,
            "Entity": f"{r.entity_type or ''} {r.entity_id or ''}".strip(),
            "Details": (r.details or "")[:200],
        }
        for r in rows
    ]
    resp = _export_if_requested(data, "audit")
    if resp:
        return resp
    usernames = [u.username for u in User.query.order_by(User.username).all()]
    return render_template("reports/audit.html", rows=data, usernames=usernames, **_report_context())


@reports_bp.route("/summary")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def summary_report():
    lang = session.get("lang", "ar")
    filters = _complaint_filters()
    total = Complaint.query.filter(*filters).count()

    by_status = (
        db.session.query(Complaint.complaint_status, func.count(Complaint.complaint_id))
        .filter(*filters)
        .group_by(Complaint.complaint_status)
        .all()
    )
    by_urgency = (
        db.session.query(Complaint.urgency, func.count(Complaint.complaint_id))
        .filter(*filters)
        .group_by(Complaint.urgency)
        .all()
    )
    by_branch = (
        db.session.query(Branch.branch_name, func.count(Complaint.complaint_id))
        .join(Complaint, Complaint.branch_code == Branch.branch_code)
        .filter(*filters)
        .group_by(Branch.branch_name)
        .order_by(func.count(Complaint.complaint_id).desc())
        .all()
    )

    status_rows = [
        {"label": translate_status(s, lang), "count": c} for s, c in by_status
    ]
    urgency_rows = [
        {"label": translate_urgency(u or "متوسطة", lang), "count": c} for u, c in by_urgency
    ]
    branch_rows = [{"label": b, "count": c} for b, c in by_branch]

    data = [{"Metric": "Total", "Value": total}]
    for row in status_rows:
        data.append({"Metric": f"Status: {row['label']}", "Value": row["count"]})
    resp = _export_if_requested(data, "summary")
    if resp:
        return resp
    return render_template(
        "reports/summary.html",
        total=total,
        status_rows=status_rows,
        urgency_rows=urgency_rows,
        branch_rows=branch_rows,
        **_report_context(),
    )


@reports_bp.route("/customers")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def customers_report():
    phone = request.args.get("phone", "").strip()
    city = request.args.get("city", "").strip()
    q = Customer.query
    if phone:
        q = q.filter(Customer.phone_number.contains(phone))
    if city:
        q = q.filter(Customer.city.contains(city))
    rows = q.order_by(Customer.id).all()
    data = [
        {
            "First Name": r.first_name,
            "Last Name": r.last_name,
            "Phone": r.phone_number,
            "City": r.city,
            "Region": r.region,
        }
        for r in rows
    ]
    resp = _export_if_requested(data, "customers")
    if resp:
        return resp
    return render_template("reports/customers.html", rows=data, **_report_context())
