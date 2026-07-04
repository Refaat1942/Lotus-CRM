"""Initialize database, migrate schema, seed features and admin user."""
import os
import sys

from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    AppSetting,
    Branch,
    ComplaintType,
    Employee,
    SystemFunction,
    User,
    UserFunctionAccess,
    UserPermission,
)
from app.services.access import ROLE_ADMIN, apply_role_features, sync_new_functions_to_users

DEFAULT_FUNCTIONS = [
    {
        "function_name": "لوحة الوكيل",
        "function_name_en": "Agent Dashboard",
        "route_name": "main.agent_home",
        "icon": "🏠",
        "color_hex": "#00796B",
        "sort_order": 0,
    },
    {
        "function_name": "تسجيل شكوى",
        "function_name_en": "New Complaint",
        "route_name": "complaints.new_complaint",
        "icon": "📝",
        "color_hex": "#4CAF50",
        "sort_order": 1,
    },
    {
        "function_name": "جميع الشكاوى",
        "function_name_en": "All Complaints",
        "route_name": "complaints.list_complaints",
        "icon": "📋",
        "color_hex": "#7B1FA2",
        "sort_order": 2,
    },
    {
        "function_name": "شكاوىي اليوم",
        "function_name_en": "My Complaints Today",
        "route_name": "complaints.my_complaints",
        "icon": "📌",
        "color_hex": "#00897B",
        "sort_order": 3,
    },
    {
        "function_name": "بحث عميل",
        "function_name_en": "Search Customer",
        "route_name": "customers.search",
        "icon": "🔍",
        "color_hex": "#0288D1",
        "sort_order": 4,
    },
    {
        "function_name": "إضافة عميل",
        "function_name_en": "Add Customer",
        "route_name": "customers.add",
        "icon": "👤",
        "color_hex": "#0097A7",
        "sort_order": 5,
    },
    {
        "function_name": "قاعدة المعرفة",
        "function_name_en": "Knowledge Base",
        "route_name": "knowledge.index",
        "icon": "💊",
        "color_hex": "#00695C",
        "sort_order": 6,
    },
    {
        "function_name": "لوحة الشكاوى",
        "function_name_en": "Complaints Dashboard",
        "route_name": "complaints.dashboard",
        "icon": "📊",
        "color_hex": "#512DA8",
        "sort_order": 7,
    },
    {
        "function_name": "لوحة الفروع",
        "function_name_en": "Branch Dashboard",
        "route_name": "complaints.branch_dashboard",
        "icon": "🏢",
        "color_hex": "#3949AB",
        "sort_order": 8,
    },
    {
        "function_name": "التقارير",
        "function_name_en": "Reports",
        "route_name": "reports.index",
        "icon": "📈",
        "color_hex": "#5E35B1",
        "sort_order": 9,
    },
    {
        "function_name": "لوحة الإدارة",
        "function_name_en": "Admin Panel",
        "route_name": "admin.index",
        "icon": "⚙️",
        "color_hex": "#455A64",
        "sort_order": 10,
    },
]

SAMPLE_BRANCHES = [
    ("B001", "Lotus Maadi", "manager.maadi@lotuspharmacies.com", "area.cairo@lotuspharmacies.com", "sales@lotuspharmacies.com"),
    ("B002", "Lotus Heliopolis", "manager.heliopolis@lotuspharmacies.com", "area.cairo@lotuspharmacies.com", "sales@lotuspharmacies.com"),
    ("B003", "Lotus Alexandria", "manager.alex@lotuspharmacies.com", "area.alex@lotuspharmacies.com", "sales@lotuspharmacies.com"),
]

SAMPLE_EMPLOYEES = [
    ("E001", "Ahmed Hassan", "B001"),
    ("E002", "Sara Mohamed", "B002"),
    ("E003", "Omar Ali", "B003"),
]

DEFAULT_COMPLAINT_TYPES = [
    ("تأخير", "Delay", False),
    ("منتج خاطئ", "Wrong Product", False),
    ("معاملة سيئة", "Bad Service", False),
    ("أخرى", "Other", False),
    ("نقص ادويه", "Medicine Shortage", False),
    ("بديل غير مناسب", "Bad Substitute", False),
    ("مشكلة اون لاين", "Online Issue", True),
]


def _migrate_schema():
    inspector = inspect(db.engine)
    if "admin_users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("admin_users")}
        if "role" not in cols:
            db.session.execute(text("ALTER TABLE admin_users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))
        if "employee_code" not in cols:
            db.session.execute(text("ALTER TABLE admin_users ADD COLUMN employee_code VARCHAR(20)"))
    if "employees" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("employees")}
        if "branch_code" not in cols:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN branch_code VARCHAR(20)"))
        if "is_active" not in cols:
            db.session.execute(text("ALTER TABLE employees ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
    if "complaint_details" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("complaint_details")}
        if "action_type" not in cols:
            db.session.execute(text("ALTER TABLE complaint_details ADD COLUMN action_type VARCHAR(40) DEFAULT 'note'"))
    db.session.commit()


def _ensure_functions():
    existing = {f.route_name for f in SystemFunction.query.all()}
    for fn in DEFAULT_FUNCTIONS:
        if fn["route_name"] not in existing:
            db.session.add(SystemFunction(**fn, is_enabled=True))
    db.session.commit()


def init_db():
    app = create_app()
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        db.create_all()
        _migrate_schema()
        _ensure_functions()

        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(username="admin", role=ROLE_ADMIN)
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
        else:
            admin.role = ROLE_ADMIN

        apply_role_features(admin, ROLE_ADMIN)

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
            for code, name, branch in SAMPLE_EMPLOYEES:
                db.session.add(
                    Employee(employee_code=code, employee_name=name, branch_code=branch, is_active=True)
                )

        if ComplaintType.query.count() == 0:
            for i, (ar, en, online) in enumerate(DEFAULT_COMPLAINT_TYPES):
                db.session.add(
                    ComplaintType(name_ar=ar, name_en=en, requires_online=online, sort_order=i, is_active=True)
                )

        defaults = {
            "brand_name": "Lotus CRM",
            "primary_color": "#00796b",
            "notification_email": "",
            "smtp_host": "",
            "smtp_port": "587",
            "use_graph_api": "0",
            "logo_path": "",
        }
        for key, val in defaults.items():
            if not AppSetting.query.filter_by(key=key).first():
                db.session.add(AppSetting(key=key, value=val))

        db.session.commit()
        sync_new_functions_to_users()
        print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
