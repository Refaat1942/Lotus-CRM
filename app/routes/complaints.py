from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Branch, Complaint, ComplaintDetail, ComplaintType, Customer, Employee
from app.services.audit import log_action
from app.services.email import (
    get_escalation_recipient_emails,
    get_escalation_recipient_rows,
    send_complaint_notification,
    send_escalation_notification,
)
from app.services.complaints import (
    build_dashboard_overview,
    complaint_display_number,
    generate_complaint_serial,
    my_complaints_filter,
)
from app.services.complaint_categories import (
    CATEGORIES,
    CATEGORY_KEYS,
    DIGITAL_PLATFORMS,
    ONLINE_SOURCES,
    category_label_key,
)
from app.services.complaint_summary import build_complaint_summary
from app.services.customer_data import customer_public_dict, find_by_phone, full_name, read_customer
from app.services.i18n import translate, translate_shift, translate_status, translate_urgency
from app.services.urgency import URGENCIES, URGENCY_DEFAULT

complaints_bp = Blueprint("complaints", __name__)

ONLINE_CHANNELS = ["Instashop", "Talabat", "Chefaa", "Website", "Lotus Pharmacies App"]
STATUSES = ["مفتوحة", "جاري الحل", "مغلقة"]


def _active_types():
    return ComplaintType.query.filter_by(is_active=True).order_by(ComplaintType.sort_order).all()


def _types_by_category(lang="ar"):
    grouped = {key: [] for key, _ in CATEGORIES}
    fallback = []
    for ct in _active_types():
        entry = {"value": ct.name_ar, "label": ct.display_name(lang)}
        cat = (ct.category or "delivery").strip().lower()
        if cat not in grouped:
            cat = "delivery"
        grouped[cat].append(entry)
        fallback.append(entry)
    if fallback:
        for key in grouped:
            if not grouped[key]:
                grouped[key] = list(fallback)
    return grouped


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


def _creator_identity():
    """Logged-in user — no separate employee selection on the form."""
    emp = _agent_employee()
    if emp:
        return emp.employee_code, emp.employee_name
    return current_user.employee_code, current_user.username


def _agent_name():
    return _creator_identity()[1]


def _active_agents():
    return Employee.query.filter_by(is_active=True).order_by(Employee.employee_name).all()


def _my_complaints_filter():
    return my_complaints_filter(current_user)


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
        emp_code, agent_name = _creator_identity()
        branch_code = request.form.get("branch_code")
        if not branch_code:
            emp = _agent_employee()
            branch_code = emp.branch_code if emp else None
        phone = request.form.get("phone", "").strip()
        category = request.form.get("complaint_category", "delivery")
        if category not in CATEGORY_KEYS:
            category = "delivery"
        ctype = request.form.get("complaint_type")
        text = request.form.get("complaint_text", "").strip()
        channel_detail = request.form.get("channel_detail") or None
        online_channel = None
        if category == "digital" and channel_detail in DIGITAL_PLATFORMS:
            online_channel = channel_detail
        elif category == "online" and channel_detail in ONLINE_SOURCES:
            online_channel = channel_detail
        urgency = request.form.get("urgency", URGENCY_DEFAULT)
        if urgency not in URGENCIES:
            urgency = URGENCY_DEFAULT

        if not all([branch_code, phone, text, ctype]):
            flash("required_fields", "error")
            return redirect(url_for("complaints.new_complaint", phone=phone))

        emp = Employee.query.get(emp_code) if emp_code else None
        if emp:
            agent_name = emp.employee_name
        now = datetime.now()
        serial = generate_complaint_serial(branch_code, now)
        complaint = Complaint(
            phone_number=phone,
            serial_number=serial,
            complaint_type=ctype,
            complaint_category=category,
            online_channel=online_channel,
            channel_detail=channel_detail,
            complaint_text=text,
            complaint_date=now,
            complaint_status="مفتوحة",
            urgency=urgency,
            created_by_code=emp_code,
            created_by_name=agent_name,
            assigned_to_code=emp_code,
            assigned_to_name=agent_name,
            branch_code=branch_code,
            shift=_shift(now),
        )
        db.session.add(complaint)
        db.session.flush()
        _add_timeline(
            complaint.complaint_id,
            agent_name,
            f"Complaint {serial} created — status: مفتوحة",
            "created",
        )
        log_action("complaint.create", "complaint", complaint.complaint_id, f"{serial} phone={phone}")

        try:
            body = (
                f"Serial  : {serial}\nAgent   : {agent_name}\nPhone   : {phone}\nType    : {ctype}\n"
                f"Urgency : {urgency}\nCategory: {category}\nChannel : {channel_detail or '—'}\nBranch  : {branch_code}\nShift   : {complaint.shift}\n\nText:\n{text}"
            )
            send_complaint_notification(branch_code, body)
        except Exception:
            flash("email_failed", "warning")

        db.session.commit()
        flash(f"serial:{serial}", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=complaint.complaint_id))

    lang = session.get("lang", "ar")
    return render_template(
        "complaints/new.html",
        branches=branches,
        complaint_types=types,
        categories=CATEGORIES,
        types_by_category=_types_by_category(lang),
        digital_platforms=DIGITAL_PLATFORMS,
        online_sources=ONLINE_SOURCES,
        prefill_phone=prefill_phone,
        default_branch=agent.branch_code if agent else None,
        urgencies=URGENCIES,
    )


@complaints_bp.route("/api/customer/<phone>")
@login_required
@feature_required("complaints.new_complaint")
def lookup_customer(phone):
    cust = find_by_phone(phone)
    if not cust:
        return jsonify({"found": False})
    return jsonify(customer_public_dict(cust))


@complaints_bp.route("/list", methods=["GET"])
@login_required
@feature_required("complaints.list_complaints")
def list_complaints():
    branches = Branch.query.order_by(Branch.branch_name).all()
    agents = _active_agents()
    return render_template(
        "complaints/list.html", branches=branches, statuses=STATUSES, agents=agents
    )


@complaints_bp.route("/api/search")
@login_required
@feature_required("complaints.list_complaints")
def search_complaints():
    lang = request.args.get("lang") or session.get("lang", "ar")
    if lang not in ("ar", "en"):
        lang = "ar"
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    status = request.args.get("status", "الكل")
    phone = request.args.get("phone", "").strip()
    serial = request.args.get("serial", "").strip()
    creator = request.args.get("creator", "").strip()
    assigned = request.args.get("assigned", "الكل")
    shift = request.args.get("shift", "الكل")
    branch = request.args.get("branch", "الكل")
    escalated = request.args.get("escalated", "")

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
    if serial:
        q = q.filter(Complaint.serial_number.ilike(f"%{serial}%"))
    if creator:
        q = q.filter(Complaint.created_by_name.contains(creator))
    if assigned == "unassigned":
        q = q.filter(Complaint.assigned_to_code.is_(None))
    elif assigned and assigned not in ("الكل", "all", ""):
        q = q.filter(Complaint.assigned_to_code == assigned)
    if shift and shift != "الكل":
        q = q.filter(Complaint.shift == shift)
    if branch and branch != "الكل":
        q = q.filter(Complaint.branch_code == branch)
    if escalated == "1":
        q = q.filter(Complaint.is_escalated.is_(True))

    rows = q.order_by(Complaint.complaint_date.desc()).limit(500).all()
    type_map = {t.name_ar: t.display_name(lang) for t in ComplaintType.query.all()}
    result = []
    now = datetime.now()
    for c in rows:
        cust = find_by_phone(c.phone_number)
        cust_data = read_customer(cust) if cust else None
        cust_name = full_name(cust_data) if cust_data else ""
        alert = c.complaint_status == "مفتوحة" and (now - c.complaint_date).days >= 1
        cat_key = c.complaint_category or "delivery"
        result.append(
            {
                "id": c.complaint_id,
                "serial": complaint_display_number(c),
                "phone": c.phone_number,
                "customer": cust_name,
                "category": translate(category_label_key(cat_key), lang),
                "channel": c.channel_detail or c.online_channel or "",
                "type_label": type_map.get(c.complaint_type, c.complaint_type),
                "date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "status_label": translate_status(c.complaint_status, lang),
                "branch": c.branch.branch_name if c.branch else c.branch_code,
                "creator": c.created_by_name,
                "assigned": c.assigned_to_name or "",
                "urgency": c.urgency or "متوسطة",
                "urgency_label": translate_urgency(c.urgency or "متوسطة", lang),
                "shift_label": translate_shift(c.shift, lang),
                "alert": alert,
                "escalated": bool(c.is_escalated),
                "summary": build_complaint_summary(c, cust_data, lang),
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
        elif action == "assign":
            emp_code = request.form.get("assigned_to_code", "").strip()
            if emp_code:
                emp = Employee.query.get(emp_code)
                if emp:
                    old_name = complaint.assigned_to_name or "—"
                    complaint.assigned_to_code = emp.employee_code
                    complaint.assigned_to_name = emp.employee_name
                    complaint.last_modified = datetime.utcnow()
                    _add_timeline(
                        complaint_id,
                        modifier,
                        f"Assigned to: {emp.employee_name}",
                        "assign",
                    )
                    log_action(
                        "complaint.assign",
                        "complaint",
                        complaint_id,
                        f"{old_name} → {emp.employee_name}",
                    )
            else:
                old_name = complaint.assigned_to_name
                complaint.assigned_to_code = None
                complaint.assigned_to_name = None
                complaint.last_modified = datetime.utcnow()
                _add_timeline(
                    complaint_id,
                    modifier,
                    "Assignment cleared — unassigned",
                    "assign",
                )
                log_action(
                    "complaint.assign",
                    "complaint",
                    complaint_id,
                    f"{old_name or '—'} → unassigned",
                )
        elif action == "urgency":
            new_u = request.form.get("urgency", complaint.urgency)
            if new_u in URGENCIES and new_u != complaint.urgency:
                old_u = complaint.urgency
                complaint.urgency = new_u
                complaint.last_modified = datetime.utcnow()
                _add_timeline(
                    complaint_id,
                    modifier,
                    f"Urgency changed: {old_u} → {new_u}",
                    "status",
                )
                log_action("complaint.urgency", "complaint", complaint_id, f"{old_u} → {new_u}")
        elif action == "escalate" and not complaint.is_escalated:
            reason = request.form.get("escalation_reason", "").strip()
            complaint.is_escalated = True
            complaint.escalated_at = datetime.utcnow()
            complaint.escalated_by = modifier
            complaint.escalation_reason = reason or None
            complaint.last_modified = datetime.utcnow()
            serial = complaint_display_number(complaint)
            recipients = get_escalation_recipient_emails(complaint.branch_code)
            complaint.escalation_recipients = ", ".join(recipients) if recipients else None
            recipient_note = ", ".join(recipients) if recipients else "—"
            _add_timeline(
                complaint_id,
                modifier,
                f"Escalated to upper management ({recipient_note})"
                + (f": {reason}" if reason else ""),
                "escalate",
            )
            log_action("complaint.escalate", "complaint", complaint_id, reason[:200] if reason else "")
            try:
                esc_cust = find_by_phone(complaint.phone_number)
                esc_data = read_customer(esc_cust) if esc_cust else None
                body = build_complaint_summary(complaint, esc_data, lang)
                if reason:
                    body += f"\n\nEscalation reason:\n{reason}"
                send_escalation_notification(complaint.branch_code, serial, body)
            except Exception:
                flash("email_failed", "warning")
            if not recipients:
                flash("escalation_no_emails", "warning")
        db.session.commit()
        flash("updated", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=complaint_id))

    cust = find_by_phone(complaint.phone_number)
    customer_data = read_customer(cust) if cust else None
    ct = ComplaintType.query.filter_by(name_ar=complaint.complaint_type).first()
    type_display = ct.display_name(lang) if ct else complaint.complaint_type
    cat_label = translate(category_label_key(complaint.complaint_category or "delivery"), lang)
    summary = build_complaint_summary(complaint, customer_data, lang)
    if complaint.is_escalated:
        if complaint.escalation_recipients:
            escalation_emails = [e.strip() for e in complaint.escalation_recipients.split(",") if e.strip()]
        else:
            escalation_emails = get_escalation_recipient_emails(complaint.branch_code)
        escalation_recipients = get_escalation_recipient_rows(complaint.branch_code, lang)
    else:
        escalation_emails = []
        escalation_recipients = get_escalation_recipient_rows(complaint.branch_code, lang)
    timeline = (
        ComplaintDetail.query.filter_by(complaint_id=complaint_id)
        .order_by(ComplaintDetail.detail_date.desc())
        .all()
    )
    return render_template(
        "complaints/detail.html",
        complaint=complaint,
        customer=customer_data,
        category_label=cat_label,
        summary=summary,
        escalation_emails=escalation_emails,
        escalation_recipients=escalation_recipients,
        timeline=timeline,
        type_display=type_display,
        statuses=STATUSES,
        urgencies=URGENCIES,
        agents=_active_agents(),
    )


@complaints_bp.route("/my")
@login_required
@feature_required("complaints.my_complaints")
def my_complaints():
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    name = _agent_name()
    rows = (
        Complaint.query.filter(
            _my_complaints_filter(),
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
    lang = session.get("lang", "ar")
    data = build_dashboard_overview(
        request.args.get("from"),
        request.args.get("to"),
        request.args.get("branch", "الكل"),
        request.args.get("status", "الكل"),
        lang,
    )
    return jsonify(data)


@complaints_bp.route("/api/dashboard-status")
@login_required
@feature_required("complaints.dashboard")
def dashboard_status_legacy():
    """Legacy status-only breakdown for older clients."""
    from sqlalchemy import func

    lang = session.get("lang", "ar")
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
    return jsonify(
        [
            {"status": r[0], "status_label": translate_status(r[0], lang), "count": r[1]}
            for r in q.all()
        ]
    )


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
