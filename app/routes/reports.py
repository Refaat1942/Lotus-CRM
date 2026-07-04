import io
from datetime import datetime

from flask import Blueprint, render_template, request, send_file
from flask_login import current_user, login_required
from openpyxl import Workbook

from app.decorators import feature_required, permission_required
from app.models import Branch, Complaint, Customer
from app.services.complaints import complaint_display_number

reports_bp = Blueprint("reports", __name__)


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


@reports_bp.route("/")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def index():
    branches = Branch.query.order_by(Branch.branch_name).all()
    return render_template("reports/index.html", branches=branches)


@reports_bp.route("/complaints")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def complaints_report():
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    branch = request.args.get("branch", "الكل")
    export = request.args.get("export")

    q = Complaint.query
    if date_from:
        q = q.filter(Complaint.complaint_date >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        q = q.filter(
            Complaint.complaint_date
            <= datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59)
        )
    if branch and branch != "الكل":
        q = q.filter(Complaint.branch_code == branch)

    rows = q.order_by(Complaint.complaint_date.desc()).all()
    data = []
    for c in rows:
        data.append(
            {
                "Serial": complaint_display_number(c),
                "ID": c.complaint_id,
                "Phone": c.phone_number,
                "Type": c.complaint_type,
                "Status": c.complaint_status,
                "Date": c.complaint_date.strftime("%Y-%m-%d %H:%M"),
                "Branch": c.branch.branch_name if c.branch else c.branch_code,
                "Text": c.complaint_text[:200],
            }
        )

    if export == "excel" and current_user.permissions.can_export_excel:
        output = _rows_to_excel(data)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"complaints_{datetime.now():%Y%m%d}.xlsx",
        )

    return render_template("reports/complaints.html", rows=data, branches=Branch.query.all())


@reports_bp.route("/customers")
@login_required
@feature_required("reports.index")
@permission_required("can_view_reports")
def customers_report():
    export = request.args.get("export")
    rows = Customer.query.order_by(Customer.id).all()
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
    if export == "excel" and current_user.permissions.can_export_excel:
        output = _rows_to_excel(data)
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"customers_{datetime.now():%Y%m%d}.xlsx",
        )
    return render_template("reports/customers.html", rows=data)
