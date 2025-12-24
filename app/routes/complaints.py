from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Branch, Complaint, ComplaintDetail, Customer, Employee
from app.services.email import send_complaint_notification

complaints_bp = Blueprint("complaints", __name__)

COMPLAINT_TYPES = [
    "تأخير",
    "منتج خاطئ",
    "معاملة سيئة",
    "أخرى",
    "نقص ادويه",
    "بديل غير مناسب",
    "مشكلة اون لاين",
]
ONLINE_CHANNELS = ["Instashop", "Talabat", "Chefaa", "Website", "Lotus Pharmacies App"]
STATUSES = ["مفتوحة", "جاري الحل", "مغلقة"]


def _shift(now=None):
    now = now or datetime.now()
    if now.hour < 8:
        return "Night"
    if now.hour < 16:
        return "Morning"
    return "After"


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required
@feature_required("complaints.new_complaint")
def new_complaint():
    employees = Employee.query.order_by(Employee.employee_name).all()
    branches = Branch.query.order_by(Branch.branch_name).all()

    if request.method == "POST":
        emp_code = request.form.get("employee_code")
        branch_code = request.form.get("branch_code")
        phone = request.form.get("phone", "").strip()
        ctype = request.form.get("complaint_type")
        text = request.form.get("complaint_text", "").strip()
        channel = request.form.get("online_channel") if ctype == "مشكلة اون لاين" else None

        if not all([emp_code, branch_code, phone, text]):
            flash("Please fill all required fields.", "error")
            return redirect(url_for("complaints.new_complaint"))

        emp = Employee.query.get(emp_code)
        now = datetime.now()
        complaint = Complaint(
            phone_number=phone,
            complaint_type=ctype,
            online_channel=channel,
            complaint_text=text,
            complaint_date=now,
            complaint_status="مفتوحة",
            created_by_code=emp_code,
            created_by_name=emp.employee_name if emp else emp_code,
            branch_code=branch_code,
            shift=_shift(now),
        )
        db.session.add(complaint)
        db.session.commit()

        try:
            details = (
                f"Employee: {emp_code} – {complaint.created_by_name}\n"
                f"Phone   : {phone}\n"
                f"Type    : {ctype}\n"
                f"Branch  : {branch_code}\n"
                f"Shift   : {complaint.shift}\n\n"
                f"Text:\n{text}"
            )
            send_complaint_notification(branch_code, details)
        except Exception as exc:
            flash(f"Complaint saved but email failed: {exc}", "warning")

        flash("complaint_saved", "success")
        return redirect(url_for("complaints.new_complaint"))

    return render_template(
        "complaints/new.html",
        employees=employees,
        branches=branches,
        complaint_types=COMPLAINT_TYPES,
        online_channels=ONLINE_CHANNELS,
    )


@complaints_bp.route("/api/customer/<phone>")
@login_required
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
    employees = Employee.query.order_by(Employee.employee_name).all()
    branches = Branch.query.order_by(Branch.branch_name).all()
    return render_template(
        "complaints/list.html",
        employees=employees,
        branches=branches,
        statuses=STATUSES,
    )


@complaints_bp.route("/api/search")
@login_required
@feature_required("complaints.list_complaints")
def search_complaints():
    from sqlalchemy import and_

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
    result = []
    now = datetime.now()
    for c in rows:
        cust = Customer.query.filter_by(phone_number=c.phone_number).first()
        cust_name = ""
        if cust:
            cust_name = f"{cust.first_name or ''} {cust.last_name or ''}".strip()
        alert = c.complaint_status == "مفتوحة" and (now - c.complaint_date).days >= 1
        result.append(
            {
                "id": c.complaint_id,
                "phone": c.phone_number,
                "customer": cust_name,
                "type": c.complaint_type,
                "date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "status": c.complaint_status,
                "branch": c.branch.branch_name if c.branch else c.branch_code,
                "creator": c.created_by_name,
                "shift": c.shift,
                "alert": alert,
            }
        )
    return jsonify(result)


@complaints_bp.route("/<int:complaint_id>", methods=["GET", "POST"])
@login_required
@feature_required("complaints.list_complaints")
def complaint_detail(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    employees = [e.employee_name for e in Employee.query.all()]

    if request.method == "POST":
        action = request.form.get("action")
        if action == "status":
            complaint.complaint_status = request.form.get("status", complaint.complaint_status)
            complaint.last_modified = datetime.utcnow()
        elif action == "note":
            detail = ComplaintDetail(
                complaint_id=complaint_id,
                modifier=request.form.get("modifier", current_user.username),
                detail_text=request.form.get("detail_text", ""),
            )
            db.session.add(detail)
        db.session.commit()
        flash("Updated.", "success")
        return redirect(url_for("complaints.complaint_detail", complaint_id=complaint_id))

    cust = Customer.query.filter_by(phone_number=complaint.phone_number).first()
    return render_template(
        "complaints/detail.html",
        complaint=complaint,
        customer=cust,
        employees=employees,
        statuses=STATUSES,
    )


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
    data = [{"status": r[0], "count": r[1]} for r in q.all()]
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
