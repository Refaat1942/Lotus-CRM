"""Reset admin password to admin/admin (run inside Docker or locally)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, UserFunctionAccess, UserPermission
from scripts.init_db import DEFAULT_FUNCTIONS, init_db


def reset_admin(password="admin"):
    app = create_app()
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin")
            db.session.add(admin)
            db.session.flush()
            db.session.add(
                UserPermission(
                    user_id=admin.id,
                    can_view_reports=True,
                    can_edit_functions=True,
                    can_manage_users=True,
                    can_export_excel=True,
                )
            )
        admin.set_password(password)
        admin.is_active = True
        db.session.commit()
        init_db()
        print(f"Admin password reset. Username: admin  Password: {password}")


if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else "admin"
    reset_admin(pwd)
