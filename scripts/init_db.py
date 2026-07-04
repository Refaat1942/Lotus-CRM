"""Initialize database, migrate schema, seed features and admin user."""
import os
import sys

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import (
    AppSetting,
    AuditLog,
    Branch,
    Complaint,
    ComplaintDetail,
    ComplaintType,
    Customer,
    Employee,
    ProductKnowledge,
    SystemFunction,
    User,
    UserFunctionAccess,
    UserPermission,
)
from app.services.access import ROLE_ADMIN, apply_role_features, sync_new_functions_to_users

DEFAULT_FUNCTIONS = [
    {
        "function_name": "مكتبي",
        "function_name_en": "My Work Desk",
        "route_name": "main.agent_home",
        "icon": "🏠",
        "color_hex": "#00796B",
        "sort_order": 1,
    },
    {
        "function_name": "تسجيل شكوى",
        "function_name_en": "New Complaint",
        "route_name": "complaints.new_complaint",
        "icon": "📝",
        "color_hex": "#4CAF50",
        "sort_order": 10,
    },
    {
        "function_name": "جميع الشكاوى",
        "function_name_en": "All Complaints",
        "route_name": "complaints.list_complaints",
        "icon": "📋",
        "color_hex": "#7B1FA2",
        "sort_order": 11,
    },
    {
        "function_name": "شكاوىي اليوم",
        "function_name_en": "My Complaints Today",
        "route_name": "complaints.my_complaints",
        "icon": "📌",
        "color_hex": "#00897B",
        "sort_order": 12,
    },
    {
        "function_name": "بحث عميل",
        "function_name_en": "Search Customer",
        "route_name": "customers.search",
        "icon": "🔍",
        "color_hex": "#0288D1",
        "sort_order": 20,
    },
    {
        "function_name": "إضافة عميل",
        "function_name_en": "Add Customer",
        "route_name": "customers.add",
        "icon": "👤",
        "color_hex": "#0097A7",
        "sort_order": 21,
    },
    {
        "function_name": "لوحة عامة",
        "function_name_en": "Overview Dashboard",
        "route_name": "complaints.dashboard",
        "icon": "📊",
        "color_hex": "#512DA8",
        "sort_order": 30,
    },
    {
        "function_name": "التقارير",
        "function_name_en": "Reports",
        "route_name": "reports.index",
        "icon": "📈",
        "color_hex": "#5E35B1",
        "sort_order": 31,
    },
    {
        "function_name": "مراقبة مباشرة",
        "function_name_en": "Live Monitor",
        "route_name": "admin.live_monitor",
        "icon": "📡",
        "color_hex": "#D32F2F",
        "sort_order": 40,
    },
    {
        "function_name": "لوحة الإدارة",
        "function_name_en": "Admin Settings",
        "route_name": "admin.index",
        "icon": "⚙️",
        "color_hex": "#455A64",
        "sort_order": 41,
    },
    {
        "function_name": "سجل التدقيق",
        "function_name_en": "Audit Logs",
        "route_name": "admin.audit_logs",
        "icon": "📜",
        "color_hex": "#546E7A",
        "sort_order": 42,
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


def _pg_error_text(exc):
    if hasattr(exc, "orig") and exc.orig is not None:
        return str(exc.orig)
    return str(exc)


def _create_table_safe(table):
    """Create one table; recover from orphaned PostgreSQL type names."""
    try:
        table.create(db.engine, checkfirst=True)
        return
    except IntegrityError as exc:
        db.session.rollback()
        err = _pg_error_text(exc)
        if "pg_type_typname_nsp_index" not in err and "already exists" not in err:
            raise

        inspector = inspect(db.engine)
        if table.name in inspector.get_table_names():
            return

        db.session.execute(text(f'DROP TYPE IF EXISTS "{table.name}" CASCADE'))
        db.session.commit()
        table.create(db.engine, checkfirst=True)


def _ensure_database_schema():
    """Create schema on fresh DB; on existing DB only add missing tables + columns."""
    inspector = inspect(db.engine)
    existing = set(inspector.get_table_names())

    if not existing:
        db.create_all()
        db.session.commit()
        return

    for table in db.metadata.sorted_tables:
        if table.name in existing:
            continue
        _create_table_safe(table)
    db.session.commit()


def _migrate_schema():
    """Safe additive migrations — every ALTER uses IF NOT EXISTS (PostgreSQL)."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    if "admin_users" in tables:
        db.session.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'admin'"))
        db.session.execute(text("ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS employee_code VARCHAR(20)"))
    if "employees" in tables:
        db.session.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS branch_code VARCHAR(20)"))
        db.session.execute(text("ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
    if "complaint_details" in tables:
        db.session.execute(
            text("ALTER TABLE complaint_details ADD COLUMN IF NOT EXISTS action_type VARCHAR(40) DEFAULT 'note'")
        )
    if "complaints" in tables:
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_to_code VARCHAR(20)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_to_name VARCHAR(120)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS serial_number VARCHAR(24)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS urgency VARCHAR(20) DEFAULT 'متوسطة'"))
        db.session.execute(text("UPDATE complaints SET urgency = 'متوسطة' WHERE urgency IS NULL"))
        db.session.execute(
            text(
                "UPDATE complaints SET serial_number = 'CMP-' || "
                "to_char(complaint_date, 'YYYYMMDD') || '-' || "
                "lpad(complaint_id::text, 4, '0') "
                "WHERE serial_number IS NULL"
            )
        )
        db.session.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_complaints_serial_number "
                "ON complaints (serial_number)"
            )
        )
        db.session.execute(
            text(
                "UPDATE complaints SET assigned_to_code = created_by_code, "
                "assigned_to_name = created_by_name "
                "WHERE assigned_to_code IS NULL AND created_by_code IS NOT NULL"
            )
        )
    if "branches" in tables:
        db.session.execute(text("ALTER TABLE branches ADD COLUMN IF NOT EXISTS owner_email VARCHAR(200)"))
    try:
        db.session.commit()
    except ProgrammingError:
        db.session.rollback()
        raise


def _ensure_functions():
    existing = {f.route_name: f for f in SystemFunction.query.all()}
    for fn in DEFAULT_FUNCTIONS:
        row = existing.get(fn["route_name"])
        if not row:
            db.session.add(SystemFunction(**fn, is_enabled=True))
        else:
            row.function_name = fn["function_name"]
            row.function_name_en = fn["function_name_en"]
            row.icon = fn["icon"]
            row.color_hex = fn["color_hex"]
            row.sort_order = fn["sort_order"]
            row.is_enabled = True
    db.session.commit()


def _disable_legacy_modules():
    """Turn off removed modules (knowledge base) for all users."""
    from app.models import SystemFunction, UserFunctionAccess

    legacy_routes = ("knowledge.index", "complaints.branch_dashboard")
    for route in legacy_routes:
        func = SystemFunction.query.filter_by(route_name=route).first()
        if not func:
            continue
        func.is_enabled = False
        UserFunctionAccess.query.filter_by(function_id=func.id).update({"is_visible": False})
    db.session.commit()


def _dedupe_menu_functions():
    """Remove duplicate menu rows (same route_name) left from older seeds."""
    from collections import defaultdict

    grouped = defaultdict(list)
    for func in SystemFunction.query.order_by(SystemFunction.id).all():
        grouped[func.route_name].append(func)

    changed = False
    for funcs in grouped.values():
        if len(funcs) <= 1:
            continue
        keep = funcs[0]
        for dup in funcs[1:]:
            for access in UserFunctionAccess.query.filter_by(function_id=dup.id).all():
                existing = UserFunctionAccess.query.filter_by(
                    user_id=access.user_id, function_id=keep.id
                ).first()
                if existing:
                    existing.is_visible = existing.is_visible or access.is_visible
                    db.session.delete(access)
                else:
                    access.function_id = keep.id
            db.session.delete(dup)
            changed = True
    if changed:
        db.session.commit()


def init_db():
    app = create_app()
    with app.app_context():
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        _ensure_database_schema()
        _migrate_schema()
        _ensure_functions()
        _disable_legacy_modules()
        _dedupe_menu_functions()

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
            "notify_stale_hours": "24",
            "notify_immediate": "1",
            "notify_assigned_only": "0",
        }
        for key, val in defaults.items():
            if not AppSetting.query.filter_by(key=key).first():
                db.session.add(AppSetting(key=key, value=val))

        db.session.commit()
        sync_new_functions_to_users()
        print("Database initialized successfully.")


if __name__ == "__main__":
    init_db()
