from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Branch, Complaint, ComplaintDetail, ComplaintType, Customer, Employee
from app.services.audit import log_action
from app.services.email import send_complaint_notification
from app.services.i18n import translate_shift, translate_status

complaints_bp = Blueprint("complaints", __name__)

ONLINE_CHANNELS = ["Instashop", "Talabat", "Chefaa", "Website", "Lotus Pharmacies App"]
STATUSES = ["مفتوحة", "جاري الحل", "مغلقة"]


def _active_types():
    return ComplaintType.query.filter_by(is_active=True).order_by(ComplaintType.sort_order).all()


def _type_requires_online(name_ar):
    ct = ComplaintType.query.filter_by(name_ar=name_ar).first()
    return ct.requires_online if ct else name_ar == "مشكلة اون لاين"


def _shift(now=None):
    now = now or datetime.now()
    if now.hour < 8:
        return "Night"
    if now.hour < 16:
        return "Morning"
    return "After"


def _agent_employee():
    if current_user.employee:
        return current_user.employee
    if current_user.employee_code:
        return Employee.query.get(current_user.employee_code)
    return None


def _agent_name():
    emp = _agent_employee()
    return emp.employee_name if emp else current_user.username


def _add_timeline(complaint_id, modifier, text, action_type="note"):
    db.session.add(
        ComplaintDetail(
            complaint_id=complaint_id,
            modifier=modifier,
            detail_text=text,
            action_type=action_type,
        )
    )


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required
@feature_required("complaints.new_complaint")
def new_complaint():
    branches = Branch.query.order_by(Branch.branch_name).all()
    agent = _agent_employee()
    prefill_phone = request.args.get("phone", "")
    types = _active_types()

    if request.method == "POST":
        emp_code = request.form.get("employee_code") or (agent.employee_code if agent else None)
        branch_code = request.form.get("branch_code") or (agent.branch_code if agent else None)
        phone = request.form.get("phone", "").strip()
        ctype = request.form.get("complaint_type")
        text = request.form.get("complaint_text", "").strip()
        channel = request.form.get("online_channel") if _type_requires_online(ctype) else None

        if not all([emp_code, branch_code, phone, text, ctype]):
            flash("required_fields", "error")
            return redirect(url_for("complaints.new_complaint", phone=phone))

        emp = Employee.query.get(emp_code)
        agent_name = emp.employee_name if emp else _agent_name()
        now = datetime.now()
        complaint = Complaint(
            phone_number=phone,
            complaint_type=ctype,
            online_channel=channel,
            complaint_text=text,
            complaint_date=now,
            complaint_status="مفتوحة",
            created_by_code=emp_code,
            created_by_name=agent_name,
            branch_code=branch_code,
            shift=_shift(now),
        )
        db.session.add(complaint)
        db.session.flush()
        _add_timeline(
            complaint.complaint_id,
            agent_name,
            f"Complaint created — status: مفتوحة",
            "created",
        )
        log_action("complaint.create", "complaint", complaint.complaint_id, f"phone={phone}")

        try:
            body = (
                f"Agent   : {agent_name}\nPhone   : {phone}\nType    : {ctype}\n"
                f"Branch  : {branch_code}\nShift   : {complaint.shift}\n\nText:\n{text}"
            )
            send_complaint_notification(branch_code, body)
        except Exception:
            flash("email_failed", "warning")

        db.session.commit()
        flash("complaint_saved", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=complaint.complaint_id))

    return render_template(
        "complaints/new.html",
        branches=branches,
        complaint_types=types,
        online_channels=ONLINE_CHANNELS,
        agent=agent,
        prefill_phone=prefill_phone,
        lang=session.get("lang", "ar"),
    )


@complaints_bp.route("/api/customer/<phone>")
@login_required
@feature_required("complaints.new_complaint")
def lookup_customer(phone):
    cust = Customer.query.filter_by(phone_number=phone).first()
    if not cust:
        return jsonify({"found": False})
    return jsonify(
        {"found": True, "name": f"{cust.first_name or ''} {cust.last_name or ''}".strip()}
    )


@complaints_bp.route("/list", methods=["GET"])
@login_required
@feature_required("complaints.list_complaints")
def list_complaints():
    branches = Branch.query.order_by(Branch.branch_name).all()
    return render_template("complaints/list.html", branches=branches, statuses=STATUSES)


@complaints_bp.route("/api/search")
@login_required
@feature_required("complaints.list_complaints")
def search_complaints():
    lang = session.get("lang", "ar")
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    status = request.args.get("status", "الكل")
    phone = request.args.get("phone", "").strip()
    creator = request.args.get("creator", "").strip()
    shift = request.args.get("shift", "الكل")
    branch = request.args.get("branch", "الكل")

    q = Complaint.query
    if date_from:
        q = q.filter(Complaint.complaint_date >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        q = q.filter(
            Complaint.complaint_date
            <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59)
        )
    if status and status != "الكل":
        q = q.filter(Complaint.complaint_status == status)
    if phone:
        q = q.filter(Complaint.phone_number.contains(phone))
    if creator:
        q = q.filter(Complaint.created_by_name.contains(creator))
    if shift and shift != "الكل":
        q = q.filter(Complaint.shift == shift)
    if branch and branch != "الكل":
        q = q.filter(Complaint.branch_code == branch)

    rows = q.order_by(Complaint.complaint_date.desc()).limit(500).all()
    type_map = {t.name_ar: t.display_name(lang) for t in ComplaintType.query.all()}
    result = []
    now = datetime.now()
    for c in rows:
        cust = Customer.query.filter_by(phone_number=c.phone_number).first()
        cust_name = f"{cust.first_name or ''} {cust.last_name or ''}".strip() if cust else ""
        alert = c.complaint_status == "مفتوحة" and (now - c.complaint_date).days >= 1
        result.append(
            {
                "id": c.complaint_id,
                "phone": c.phone_number,
                "customer": cust_name,
                "type_label": type_map.get(c.complaint_type, c.complaint_type),
                "date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "status_label": translate_status(c.complaint_status, lang),
                "branch": c.branch.branch_name if c.branch else c.branch_code,
                "creator": c.created_by_name,
                "shift_label": translate_shift(c.shift, lang),
                "alert": alert,
            }
        )
    return jsonify(result)


@complaints_bp.route("/<int:complaint_id>", methods=["GET", "POST"])
@login_required
@feature_required("complaints.list_complaints")
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    lang = session.get("lang", "ar")

    if request.method == "POST":
        action = request.form.get("action")
        modifier = _agent_name()
        if action == "status":
            old = complaint.complaint_status
            new = request.form.get("status", old)
            if new != old:
                complaint.complaint_status = new
                complaint.last_modified = datetime.utcnow()
                _add_timeline(
                    complaint_id,
                    modifier,
                    f"Status changed: {old} → {new}",
                    "status",
                )
                log_action("complaint.status", "complaint", complaint_id, f"{old} → {new}")
        elif action == "note":
            note = request.form.get("detail_text", "").strip()
            if note:
                _add_timeline(complaint_id, modifier, note, "note")
                log_action("complaint.note", "complaint", complaint_id, note[:200])
        db.session.commit()
        flash("updated", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=complaint_id))

    cust = Customer.query.filter_by(phone_number=complaint.phone_number).first()
    ct = ComplaintType.query.filter_by(name_ar=complaint.complaint_type).first()
    type_display = ct.display_name(lang) if ct else complaint.complaint_type
    timeline = (
        ComplaintDetail.query.filter_by(complaint_id=complaint_id)
        .order_by(ComplaintDetail.detail_date.desc())
        .all()
    )
    return render_template(
        "complaints/detail.html",
        complaint=complaint,
        customer=cust,
        timeline=timeline,
        type_display=type_display,
        statuses=STATUSES,
    )


@complaints_bp.route("/my")
@login_required
@feature_required("complaints.my_complaints")
def my_complaints():
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    name = _agent_name()
    rows = (
        Complaint.query.filter(
            Complaint.created_by_name == name,
            Complaint.complaint_date >= today_start,
        )
        .order_by(Complaint.complaint_date.desc())
        .all()
    )
    return render_template("complaints/my.html", rows=rows, agent_name=name)


@complaints_bp.route("/dashboard")
@login_required
@feature_required("complaints.dashboard")
def dashboard():
    branches = Branch.query.order_by(Branch.branch_name).all()
    return render_template("complaints/dashboard.html", branches=branches, statuses=STATUSES)


@complaints_bp.route("/api/dashboard-stats")
@login_required
@feature_required("complaints.dashboard")
def dashboard_stats():
    from sqlalchemy import func

    date_from = request.args.get("from")
    date_to = request.args.get("to")
    branch = request.args.get("branch", "الكل")
    status = request.args.get("status", "الكل")

    q = db.session.query(Complaint.complaint_status, func.count(Complaint.complaint_id))
    if date_from:
        q = q.filter(Complaint.complaint_date >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        q = q.filter(
            Complaint.complaint_date
            <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59)
        )
    if branch and branch != "الكل":
        q = q.filter(Complaint.branch_code == branch)
    if status and status != "الكل":
        q = q.filter(Complaint.complaint_status == status)
    q = q.group_by(Complaint.complaint_status)
    lang = session.get("lang", "ar")
    data = [
        {"status": r[0], "status_label": translate_status(r[0], lang), "count": r[1]}
        for r in q.all()
    ]
    return jsonify(data)


@complaints_bp.route("/branch-dashboard")
@login_required
@feature_required("complaints.branch_dashboard")
def branch_dashboard():
    branches = Branch.query.order_by(Branch.branch_name).all()
    return render_template("complaints/branch_dashboard.html", branches=branches)


@complaints_bp.route("/api/branch-stats")
@login_required
@feature_required("complaints.branch_dashboard")
def branch_stats():
    from sqlalchemy import func

    date_from = request.args.get("from")
    date_to = request.args.get("to")
    q = db.session.query(Branch.branch_name, func.count(Complaint.complaint_id)).join(
        Complaint, Complaint.branch_code == Branch.branch_code
    )
    if date_from:
        q = q.filter(Complaint.complaint_date >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        q = q.filter(
            Complaint.complaint_date
            <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59)
        )
    q = q.group_by(Branch.branch_name).order_by(func.count(Complaint.complaint_id).desc())
    return jsonify([{"branch": r[0], "count": r[1]} for r in q.all()])
