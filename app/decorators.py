from functools import wraps

from flask import abort, flash, redirect, session, url_for
from flask_login import current_user


def permission_required(flag_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            perms = current_user.permissions
            if not perms or not getattr(perms, flag_name, False):
                flash("Access denied.", "error")
                return redirect(url_for("main.dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def feature_required(route_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            from app.models import SystemFunction, UserFunctionAccess

            func = SystemFunction.query.filter_by(route_name=route_name, is_enabled=True).first()
            if not func:
                abort(404)
            access = UserFunctionAccess.query.filter_by(
                user_id=current_user.id, function_id=func.id
            ).first()
            if access and not access.is_visible:
                flash("This feature is not available for your account.", "error")
                return redirect(url_for("main.dashboard"))
            if not access:
                flash("This feature is not available for your account.", "error")
                return redirect(url_for("main.dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_lang():
    return session.get("lang", "ar")
