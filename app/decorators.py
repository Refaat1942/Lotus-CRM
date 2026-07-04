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
                flash("access_denied", "error")
                return redirect(url_for("main.agent_home"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def feature_required(route_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            from app.services.access import user_can_access

            if not user_can_access(current_user, route_name):
                flash("feature_denied", "error")
                return redirect(url_for("main.agent_home"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_lang():
    return session.get("lang", "ar")
