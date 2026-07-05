"""Idempotent PostgreSQL schema migrations (safe to run on every app start)."""
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.extensions import db


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
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS serial_number VARCHAR(40)"))
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
    if "complaint_types" in tables:
        db.session.execute(text("ALTER TABLE complaint_types ADD COLUMN IF NOT EXISTS category VARCHAR(40) DEFAULT 'delivery'"))
        db.session.execute(text("UPDATE complaint_types SET category = 'delivery' WHERE category IS NULL"))
        db.session.execute(text("UPDATE complaint_types SET category = 'online' WHERE name_ar = 'مشكلة اون لاين'"))
    if "complaints" in tables:
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS complaint_category VARCHAR(40)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS channel_detail VARCHAR(80)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS is_escalated BOOLEAN DEFAULT FALSE"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalated_by VARCHAR(120)"))
        db.session.execute(text("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS escalation_reason TEXT"))
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS ix_complaints_is_escalated ON complaints (is_escalated)")
        )
        db.session.execute(
            text("ALTER TABLE complaints ALTER COLUMN serial_number TYPE VARCHAR(40)")
        )
    if "customers" in tables:
        db.session.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS phone_hash VARCHAR(64)"))
        db.session.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS enc_payload TEXT"))
        db.session.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_phone_hash ON customers (phone_hash)")
        )
    if "customer_notes" not in tables:
        _create_table_safe(db.metadata.tables["customer_notes"])
    try:
        db.session.commit()
    except ProgrammingError:
        db.session.rollback()
        raise

    if "customers" in tables:
        from app.services.customer_data import encrypt_all_legacy_customers

        encrypt_all_legacy_customers()


def run_startup_migrations(app):
    """Apply schema updates when the web process starts (after init_db or on redeploy)."""
    with app.app_context():
        migrate_schema()
