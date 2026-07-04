from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Complaint, Customer

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/search", methods=["GET", "POST"])
@login_required
@feature_required("customers.search")
def search():
    customer = None
    complaints = []
    phone = request.args.get("phone", "").strip() or request.form.get("phone", "").strip()
    if phone:
        customer = Customer.query.filter_by(phone_number=phone).first()
        if customer:
            complaints = (
                Complaint.query.filter_by(phone_number=phone)
                .order_by(Complaint.complaint_date.desc())
                .limit(20)
                .all()
            )
    return render_template(
        "customers/search.html",
        customer=customer,
        complaints=complaints,
        phone=phone,
    )


@customers_bp.route("/add", methods=["GET", "POST"])
@login_required
@feature_required("customers.add")
def add():
    if request.method == "POST":
        phone = request.form.get("phone_number", "").strip()
        if not phone:
            flash("required_fields", "error")
            return redirect(url_for("customers.add"))
        if Customer.query.filter_by(phone_number=phone).first():
            flash("customer_exists", "error")
            return redirect(url_for("customers.add"))

        customer = Customer(
            first_name=request.form.get("first_name", "").strip(),
            last_name=request.form.get("last_name", "").strip(),
            phone_number=phone,
            city=request.form.get("city", "").strip(),
            region=request.form.get("region", "").strip(),
        )
        db.session.add(customer)
        db.session.commit()
        flash("customer_saved", "success")
        return redirect(url_for("customers.search", phone=phone))

    prefill_phone = request.args.get("phone", "")
    return render_template("customers/add.html", prefill_phone=prefill_phone)


@customers_bp.route("/api/lookup/<phone>")
@login_required
@feature_required("customers.search")
def lookup(phone):
    cust = Customer.query.filter_by(phone_number=phone).first()
    if not cust:
        return jsonify({"found": False})
    return jsonify(
        {
            "found": True,
            "id": cust.id,
            "name": f"{cust.first_name or ''} {cust.last_name or ''}".strip(),
            "phone": cust.phone_number,
            "city": cust.city or "",
            "region": cust.region or "",
        }
    )
