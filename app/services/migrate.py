"""Idempotent PostgreSQL schema migrations (safe to run on every app start)."""
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.extensions import db


def _pg_error_text(exc):
    if hasattr(exc, "orig") and exc.orig is not None:
        return str(exc.orig)
    return str(exc)


def _run_sql(statements):
    """Run DDL/DML with autocommit so migrations do not hold table locks."""
    with db.engine.connect() as conn:
        autocommit = conn.execution_options(isolation_level="AUTOCOMMIT")
        autocommit.execute(text("SET lock_timeout = '30s'"))
        for stmt in statements:
            if stmt:
                autocommit.execute(text(stmt))


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

        _run_sql([f'DROP TYPE IF EXISTS "{table.name}" CASCADE'])
        table.create(db.engine, checkfirst=True)


def ensure_database_schema():
    """Create schema on fresh DB; on existing DB only add missing tables."""
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


def migrate_schema():
    """Safe additive migrations — every ALTER uses IF NOT EXISTS (PostgreSQL)."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    statements = []

    if "admin_users" in tables:
        statements.extend(
            [
                "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'admin'",
                "ALTER TABLE admin_users ADD COLUMN IF NOT EXISTS employee_code VARCHAR(20)",
            ]
        )
    if "employees" in tables:
        statements.extend(
            [
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS branch_code VARCHAR(20)",
                "ALTER TABLE employees ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
            ]
        )
    if "complaint_details" in tables:
        statements.append(
            "ALTER TABLE complaint_details ADD COLUMN IF NOT EXISTS action_type VARCHAR(40) DEFAULT 'note'"
        )
    if "complaints" in tables:
        statements.extend(
            [
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_to_code VARCHAR(20)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS assigned_to_name VARCHAR(120)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS serial_number VARCHAR(40)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS urgency VARCHAR(20) DEFAULT 'متوسطة'",
                "UPDATE complaints SET urgency = 'متوسطة' WHERE urgency IS NULL",
                (
                    "UPDATE complaints SET serial_number = 'CMP-' || "
                    "to_char(complaint_date, 'YYYYMMDD') || '-' || "
                    "lpad(complaint_id::text, 4, '0') "
                    "WHERE serial_number IS NULL"
                ),
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_complaints_serial_number ON complaints (serial_number)",
                (
                    "UPDATE complaints SET assigned_to_code = created_by_code, "
                    "assigned_to_name = created_by_name "
                    "WHERE assigned_to_code IS NULL AND created_by_code IS NOT NULL"
                ),
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS complaint_category VARCHAR(40)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS channel_detail VARCHAR(80)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS is_escalated BOOLEAN DEFAULT FALSE",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalated_by VARCHAR(120)",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalation_reason TEXT",
                "ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalation_recipients VARCHAR(500)",
                "CREATE INDEX IF NOT EXISTS ix_complaints_is_escalated ON complaints (is_escalated)",
            ]
        )
    if "branches" in tables:
        statements.append("ALTER TABLE branches ADD COLUMN IF NOT EXISTS owner_email VARCHAR(200)")
    if "complaint_types" in tables:
        statements.extend(
            [
                "ALTER TABLE complaint_types ADD COLUMN IF NOT EXISTS category VARCHAR(40) DEFAULT 'delivery'",
                "UPDATE complaint_types SET category = 'delivery' WHERE category IS NULL",
                "UPDATE complaint_types SET category = 'online' WHERE name_ar = 'مشكلة اون لاين'",
                "UPDATE complaint_types SET category = 'online' WHERE category = 'delivery' AND (name_ar ILIKE '%اون%' OR name_en ILIKE '%online%')",
                "UPDATE complaint_types SET category = 'digital' WHERE category = 'delivery' AND (name_ar ILIKE '%رقم%' OR name_en ILIKE '%digital%')",
                "UPDATE complaint_types SET category = 'cash' WHERE category = 'delivery' AND (name_ar ILIKE '%دفع%' OR name_ar ILIKE '%استرداد%' OR name_en ILIKE '%payment%' OR name_en ILIKE '%refund%')",
                "UPDATE complaint_types SET category = 'insurance' WHERE category = 'delivery' AND (name_ar ILIKE '%تأمين%' OR name_en ILIKE '%insur%' OR name_en ILIKE '%coverage%' OR name_en ILIKE '%authorization%')",
            ]
        )
    if "customers" in tables:
        statements.extend(
            [
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS phone_hash VARCHAR(64)",
                "ALTER TABLE customers ADD COLUMN IF NOT EXISTS enc_payload TEXT",
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_phone_hash ON customers (phone_hash)",
            ]
        )

    if statements:
        try:
            _run_sql(statements)
        except ProgrammingError:
            db.session.rollback()
            raise

    if "complaints" in tables:
        try:
            _run_sql(["ALTER TABLE complaints ALTER COLUMN serial_number TYPE VARCHAR(40)"])
        except ProgrammingError:
            pass

    if "customer_notes" not in tables:
        _create_table_safe(db.metadata.tables["customer_notes"])

    if "customers" in tables:
        from app.models import AppSetting
        from app.services.customer_data import encrypt_all_legacy_customers

        if AppSetting.get("legacy_customers_encrypted") != "1":
            encrypt_all_legacy_customers()
            AppSetting.set("legacy_customers_encrypted", "1")


def run_startup_migrations(app):
    """Apply schema updates when the web process starts (after init_db or on redeploy)."""
    with app.app_context():
        migrate_schema()
