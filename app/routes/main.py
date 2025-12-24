from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import SystemFunction, UserFunctionAccess

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    access_rows = (
        UserFunctionAccess.query.filter_by(user_id=current_user.id, is_visible=True)
        .join(SystemFunction)
        .filter(SystemFunction.is_enabled == True, SystemFunction.parent_id.is_(None))  # noqa: E712
        .order_by(SystemFunction.sort_order)
        .all()
    )
    functions = [row.function for row in access_rows]
    return render_template("main/dashboard.html", functions=functions)
