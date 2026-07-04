from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import User
from app.services.audit import log_action

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.agent_home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            log_action("user.login", "user", user.id)
            db.session.commit()
            return redirect(url_for("main.agent_home"))
        flash("invalid_credentials", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    log_action("user.logout", "user", current_user.id)
    db.session.commit()
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/set-language/<lang>")
def set_language(lang):
    if lang in ("ar", "en"):
        session["lang"] = lang
    return redirect(request.referrer or url_for("main.agent_home"))
