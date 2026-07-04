from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import feature_required
from app.extensions import db
from app.models import Complaint, SystemFunction, UserFunctionAccess
from app.services.access import user_can_access, user_can_admin, user_can_view_reports

main_bp = Blueprint("main", __name__)


def _visible_functions():
    rows = (
        UserFunctionAccess.query.filter_by(user_id=current_user.id, is_visible=True)
        .join(SystemFunction)
        .filter(SystemFunction.is_enabled == True)  # noqa: E712
        .order_by(SystemFunction.sort_order)
        .all()
    )
    return [row.function for row in rows]


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
        Complaint.created_by_name == (current_user.employee.employee_name if current_user.employee else current_user.username),
        Complaint.complaint_date >= today_start,
    ).count()
    open_count = Complaint.query.filter_by(complaint_status="مفتوحة").count()
    recent = Complaint.query.order_by(Complaint.complaint_date.desc()).limit(5).all()
    functions = _visible_functions()
    quick = [f for f in functions if f.route_name != "main.agent_home"]
    return render_template(
        "main/agent_home.html",
        my_today=my_today,
        open_count=open_count,
        recent=recent,
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("main.agent_home"))
