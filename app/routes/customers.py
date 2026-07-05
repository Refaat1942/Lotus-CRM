from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Complaint, Customer, CustomerNote
from app.services.audit import log_action
from app.services.customer_data import (
    customer_public_dict,
    find_by_phone,
    full_name,
    read_customer,
    search_customers,
    write_customer,
)

customers_bp = Blueprint("customers", __name__)


@customers_bp.route("/search", methods=["GET", "POST"])
@login_required
@feature_required("customers.search")
def search():
    query = request.args.get("q", "").strip() or request.args.get("phone", "").strip()
    if request.method == "POST":
        query = request.form.get("q", "").strip() or request.form.get("phone", "").strip()
    results = []
    if query:
        exact = find_by_phone(query)
        if exact:
            return redirect(url_for("customers.profile", customer_id=exact.id))
        results = search_customers(query, limit=20)
    return render_template(
        "customers/search.html",
        query=query,
        results=results,
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
        if find_by_phone(phone):
            flash("customer_exists", "error")
            return redirect(url_for("customers.add"))

        customer = Customer()
        write_customer(
            customer,
            request.form.get("first_name", "").strip(),
            request.form.get("last_name", "").strip(),
            phone,
            request.form.get("city", "").strip(),
            request.form.get("region", "").strip(),
        )
        db.session.add(customer)
        db.session.commit()
        flash("customer_saved", "success")
        return redirect(url_for("customers.profile", customer_id=customer.id))

    prefill_phone = request.args.get("phone", "")
    return render_template("customers/add.html", prefill_phone=prefill_phone)


@customers_bp.route("/<int:customer_id>", methods=["GET", "POST"])
@login_required
@feature_required("customers.search")
def profile(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer_data = read_customer(customer)

    if request.method == "POST":
        note_text = request.form.get("note_text", "").strip()
        if note_text:
            db.session.add(
                CustomerNote(
                    customer_id=customer.id,
                    author_name=current_user.username,
                    note_text=note_text,
                )
            )
            db.session.commit()
            log_action(
                "customer.note",
                "customer",
                customer.id,
                note_text[:200],
            )
            flash("note_saved", "success")
        return redirect(url_for("customers.profile", customer_id=customer.id))

    phone = customer_data.get("phone_number") or ""
    complaints = (
        Complaint.query.filter_by(phone_number=phone)
        .order_by(Complaint.complaint_date.desc())
        .all()
    )
    open_count = sum(1 for c in complaints if c.complaint_status == "مفتوحة")
    in_progress = sum(1 for c in complaints if c.complaint_status == "جاري الحل")
    closed_count = sum(1 for c in complaints if c.complaint_status == "مغلقة")
    notes = CustomerNote.query.filter_by(customer_id=customer.id).order_by(
        CustomerNote.created_at.desc()
    ).all()

    return render_template(
        "customers/profile.html",
        customer=customer,
        customer_data=customer_data,
        complaints=complaints,
        notes=notes,
        stats={
            "total": len(complaints),
            "open": open_count,
            "in_progress": in_progress,
            "closed": closed_count,
            "last_date": complaints[0].complaint_date if complaints else None,
        },
    )


@customers_bp.route("/api/lookup/<phone>")
@login_required
@feature_required("customers.search")
def lookup(phone):
    cust = find_by_phone(phone)
    if not cust:
        return jsonify({"found": False})
    return jsonify(customer_public_dict(cust))


@customers_bp.route("/api/search")
@login_required
@feature_required("customers.search")
def api_search():
    q = request.args.get("q", "").strip()
    return jsonify(search_customers(q, limit=25))
