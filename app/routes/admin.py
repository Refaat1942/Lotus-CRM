import hashlib

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.decorators import permission_required
from app.extensions import db
from app.models import AppSetting, Branch, SystemFunction, User, UserFunctionAccess, UserPermission

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@login_required
@permission_required("can_manage_users")
def index():
    users = User.query.order_by(User.username).all()
    functions = SystemFunction.query.order_by(SystemFunction.sort_order).all()
    branches = Branch.query.order_by(Branch.branch_name).all()
    settings = {
        "brand_name": AppSetting.get("brand_name", "Lotus CRM"),
        "primary_color": AppSetting.get("primary_color", "#00796b"),
        "notification_email": AppSetting.get("notification_email", ""),
        "smtp_host": AppSetting.get("smtp_host", ""),
        "smtp_port": AppSetting.get("smtp_port", "587"),
        "smtp_user": AppSetting.get("smtp_user", ""),
        "smtp_password": AppSetting.get("smtp_password", ""),
        "use_graph_api": AppSetting.get("use_graph_api", "0"),
        "graph_tenant_id": AppSetting.get("graph_tenant_id", ""),
        "graph_client_id": AppSetting.get("graph_client_id", ""),
        "graph_client_secret": AppSetting.get("graph_client_secret", ""),
    }
    return render_template(
        "admin/index.html",
        users=users,
        functions=functions,
        branches=branches,
        settings=settings,
    )


@admin_bp.route("/users/add", methods=["POST"])
@login_required
@permission_required("can_manage_users")
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not username or not password:
        flash("Username and password required.", "error")
        return redirect(url_for("admin.index"))
    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "error")
        return redirect(url_for("admin.index"))

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(
        UserPermission(
            user_id=user.id,
            can_view_reports=True,
            can_edit_functions=False,
            can_manage_users=False,
            can_export_excel=True,
        )
    )
    for func in SystemFunction.query.filter_by(is_enabled=True).all():
        db.session.add(UserFunctionAccess(user_id=user.id, function_id=func.id, is_visible=True))
    db.session.commit()
    flash("User created.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@permission_required("can_manage_users")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == "admin":
        flash("Cannot delete admin user.", "error")
        return redirect(url_for("admin.index"))
    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/permissions/<int:user_id>", methods=["POST"])
@login_required
@permission_required("can_manage_users")
def update_permissions(user_id):
    perms = UserPermission.query.filter_by(user_id=user_id).first_or_404()
    perms.can_view_reports = "can_view_reports" in request.form
    perms.can_edit_functions = "can_edit_functions" in request.form
    perms.can_manage_users = "can_manage_users" in request.form
    perms.can_export_excel = "can_export_excel" in request.form
    db.session.commit()
    flash("Permissions updated.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/functions/<int:function_id>/toggle", methods=["POST"])
@login_required
@permission_required("can_edit_functions")
def toggle_function(function_id):
    func = SystemFunction.query.get_or_404(function_id)
    func.is_enabled = not func.is_enabled
    db.session.commit()
    return redirect(url_for("admin.index"))


@admin_bp.route("/access/toggle", methods=["POST"])
@login_required
@permission_required("can_manage_users")
def toggle_access():
    user_id = int(request.form.get("user_id"))
    function_id = int(request.form.get("function_id"))
    access = UserFunctionAccess.query.filter_by(user_id=user_id, function_id=function_id).first()
    if access:
        access.is_visible = not access.is_visible
    else:
        access = UserFunctionAccess(user_id=user_id, function_id=function_id, is_visible=True)
        db.session.add(access)
    db.session.commit()
    return redirect(url_for("admin.index"))


@admin_bp.route("/settings", methods=["POST"])
@login_required
@permission_required("can_manage_users")
def save_settings():
    keys = [
        "brand_name",
        "primary_color",
        "notification_email",
        "smtp_host",
        "smtp_port",
        "smtp_user",
        "smtp_password",
        "graph_tenant_id",
        "graph_client_id",
        "graph_client_secret",
    ]
    for key in keys:
        val = request.form.get(key, "")
        if val or key not in ("smtp_password", "graph_client_secret"):
            AppSetting.set(key, val)
    AppSetting.set("use_graph_api", "1" if request.form.get("use_graph_api") else "0")
    flash("Settings saved.", "success")
    return redirect(url_for("admin.index"))
