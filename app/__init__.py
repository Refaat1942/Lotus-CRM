import os

from flask import Flask, url_for

from app.config import Config
from app.extensions import db, login_manager
from app.models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.complaints import complaints_bp
    from app.routes.customers import customers_bp
    from app.routes.knowledge import knowledge_bp
    from app.routes.admin import admin_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(complaints_bp, url_prefix="/complaints")
    app.register_blueprint(customers_bp, url_prefix="/customers")
    app.register_blueprint(knowledge_bp, url_prefix="/knowledge")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    @app.context_processor
    def inject_globals():
        from flask import session
        from app.models import AppSetting
        from app.services.access import user_can_admin, user_can_view_reports
        from app.services.i18n import (
            translate,
            translate_complaint_type,
            translate_shift,
            translate_status,
        )

        lang = session.get("lang", app.config.get("DEFAULT_LANGUAGE", "ar"))
        brand = AppSetting.get("brand_name", "Lotus CRM")
        primary = AppSetting.get("primary_color", "#00796b")
        logo_path = AppSetting.get("logo_path", "")
        logo_url = url_for("static", filename=logo_path) if logo_path else None

        def t(key):
            return translate(key, lang)

        return dict(
            t=t,
            lang=lang,
            brand=brand,
            primary_color=primary,
            logo_url=logo_url,
            t_status=lambda v: translate_status(v, lang),
            t_type=lambda v: translate_complaint_type(v, lang),
            t_shift=lambda v: translate_shift(v, lang),
        )

    @app.context_processor
    def inject_nav_access():
        from flask import session
        from flask_login import current_user
        from app.services.access import user_can_admin, user_can_view_reports

        if not current_user.is_authenticated:
            return dict(show_reports=False, show_admin=False)
        return dict(
            show_reports=user_can_view_reports(current_user),
            show_admin=user_can_admin(current_user),
        )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)
    return app
