from datetime import datetime

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.models import Complaint
from app.services.complaints import my_complaints_filter
from app.services.access import user_can_access

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.agent_home"))
    return redirect(url_for("auth.login"))


@main_bp.route("/home")
@login_required
@feature_required("main.agent_home")
def agent_home():
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    my_today = Complaint.query.filter(
        my_complaints_filter(current_user),
        Complaint.complaint_date >= today_start,
    ).count()
    open_count = Complaint.query.filter_by(complaint_status="مفتوحة").count()
    recent = Complaint.query.order_by(Complaint.complaint_date.desc()).limit(5).all()
    return render_template(
        "main/agent_home.html",
        my_today=my_today,
        open_count=open_count,
        recent=recent,
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    if user_can_access(current_user, "complaints.dashboard"):
        return redirect(url_for("complaints.dashboard"))
    return redirect(url_for("main.agent_home"))
