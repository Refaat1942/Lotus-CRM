"""Initialize database with schema, admin user, and default features."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    AppSetting,
    Branch,
    Employee,
    SystemFunction,
    User,
    UserFunctionAccess,
    UserPermission,
)


DEFAULT_FUNCTIONS = [
    {
        "function_name": "تسجيل شكوى",
        "function_name_en": "New Complaint",
        "route_name": "complaints.new_complaint",
        "icon": "📝",
        "color_hex": "#4CAF50",
        "sort_order": 1,
    },
    {
        "function_name": "عرض الشكاوى",
        "function_name_en": "View Complaints",
        "route_name": "complaints.list_complaints",
        "icon": "📋",
        "color_hex": "#7B1FA2",
        "sort_order": 2,
    },
    {
        "function_name": "لوحة الشكاوى",
        "function_name_en": "Complaints Dashboard",
        "route_name": "complaints.dashboard",
        "icon": "📊",
        "color_hex": "#512DA8",
        "sort_order": 3,
    },
    {
        "function_name": "لوحة الفروع",
        "function_name_en": "Branch Dashboard",
        "route_name": "complaints.branch_dashboard",
        "icon": "🏢",
        "color_hex": "#0288D1",
        "sort_order": 4,
    },
    {
        "function_name": "قاعدة المعرفة",
        "function_name_en": "Knowledge Base",
        "route_name": "knowledge.index",
        "icon": "💊",
        "color_hex": "#00796B",
        "sort_order": 5,
    },
    {
        "function_name": "التقارير",
        "function_name_en": "Reports",
        "route_name": "reports.index",
        "icon": "📈",
        "color_hex": "#3949AB",
        "sort_order": 6,
    },
]

SAMPLE_BRANCHES = [
    ("B001", "Lotus Maadi", "manager.maadi@lotuspharmacies.com", "area.cairo@lotuspharmacies.com", "sales@lotuspharmacies.com"),
    ("B002", "Lotus Heliopolis", "manager.heliopolis@lotuspharmacies.com", "area.cairo@lotuspharmacies.com", "sales@lotuspharmacies.com"),
    ("B003", "Lotus Alexandria", "manager.alex@lotuspharmacies.com", "area.alex@lotuspharmacies.com", "sales@lotuspharmacies.com"),
]

SAMPLE_EMPLOYEES = [
    ("E001", "Ahmed Hassan"),
    ("E002", "Sara Mohamed"),
    ("E003", "Omar Ali"),
]


def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin")
            admin.set_password("admin")
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
            print("Created admin user (username: admin, password: admin)")

        if SystemFunction.query.count() == 0:
            for fn in DEFAULT_FUNCTIONS:
                db.session.add(SystemFunction(**fn, is_enabled=True))
            db.session.flush()
            print(f"Created {len(DEFAULT_FUNCTIONS)} system functions")

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("ERROR: admin user missing. Run scripts/reset_admin.py")
            db.session.commit()
            return

        for func in SystemFunction.query.all():
            exists = UserFunctionAccess.query.filter_by(
                user_id=admin.id, function_id=func.id
            ).first()
            if not exists:
                db.session.add(
                    UserFunctionAccess(user_id=admin.id, function_id=func.id, is_visible=True)
                )

        if Branch.query.count() == 0:
            for code, name, mgr, area, sales in SAMPLE_BRANCHES:
                db.session.add(
                    Branch(
                        branch_code=code,
                        branch_name=name,
                        branch_manager_email=mgr,
                        area_manager_email=area,
                        sales_manager_email=sales,
                    )
                )

        if Employee.query.count() == 0:
            for code, name in SAMPLE_EMPLOYEES:
                db.session.add(Employee(employee_code=code, employee_name=name))

        defaults = {
            "brand_name": "Lotus CRM",
            "primary_color": "#00796b",
            "notification_email": "",
            "smtp_host": "",
            "smtp_port": "587",
            "use_graph_api": "0",
        }
        for key, val in defaults.items():
            if not AppSetting.query.filter_by(key=key).first():
                db.session.add(AppSetting(key=key, value=val))

        db.session.commit()
        print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
