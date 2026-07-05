from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="agent")
    employee_code = db.Column(db.String(20), db.ForeignKey("employees.employee_code"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship(
        "UserPermission", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    function_access = db.relationship(
        "UserFunctionAccess", back_populates="user", cascade="all, delete-orphan"
    )
    employee = db.relationship("Employee", foreign_keys=[employee_code])

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if check_password_hash(self.password_hash, password):
            return True
        import hashlib

        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()


class UserPermission(db.Model):
    __tablename__ = "user_permissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), unique=True)
    can_view_reports = db.Column(db.Boolean, default=True)
    can_edit_functions = db.Column(db.Boolean, default=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_export_excel = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="permissions")


class SystemFunction(db.Model):
    __tablename__ = "system_functions"

    id = db.Column(db.Integer, primary_key=True)
    function_name = db.Column(db.String(120), nullable=False)
    function_name_en = db.Column(db.String(120))
    route_name = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(40), default="📋")
    color_hex = db.Column(db.String(20), default="#3498DB")
    is_enabled = db.Column(db.Boolean, default=True)
    is_subfeature = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("system_functions.id"), nullable=True)
    sort_order = db.Column(db.Integer, default=0)

    parent = db.relationship("SystemFunction", remote_side=[id], backref="subfeatures")
    user_access = db.relationship("UserFunctionAccess", back_populates="function")


class UserFunctionAccess(db.Model):
    __tablename__ = "user_function_access"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=False)
    function_id = db.Column(db.Integer, db.ForeignKey("system_functions.id"), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="function_access")
    function = db.relationship("SystemFunction", back_populates="user_access")

    __table_args__ = (db.UniqueConstraint("user_id", "function_id"),)


class Branch(db.Model):
    __tablename__ = "branches"

    branch_code = db.Column(db.String(20), primary_key=True)
    branch_name = db.Column(db.String(120), nullable=False)
    branch_manager_email = db.Column(db.String(200))
    area_manager_email = db.Column(db.String(200))
    sales_manager_email = db.Column(db.String(200))
    owner_email = db.Column(db.String(200))


class Employee(db.Model):
    __tablename__ = "employees"

    employee_code = db.Column(db.String(20), primary_key=True)
    employee_name = db.Column(db.String(120), nullable=False)
    branch_code = db.Column(db.String(20), db.ForeignKey("branches.branch_code"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    branch = db.relationship("Branch")


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone_number = db.Column(db.String(30), unique=True, index=True)
    city = db.Column(db.String(80))
    region = db.Column(db.String(80))
    phone_hash = db.Column(db.String(64), unique=True, index=True)
    enc_payload = db.Column(db.Text)

    notes = db.relationship(
        "CustomerNote",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="CustomerNote.created_at.desc()",
    )


class CustomerNote(db.Model):
    __tablename__ = "customer_notes"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    author_name = db.Column(db.String(120))
    note_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    customer = db.relationship("Customer", back_populates="notes")


class Complaint(db.Model):
    __tablename__ = "complaints"

    complaint_id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(40), unique=True, index=True)
    phone_number = db.Column(db.String(30), nullable=False)
    complaint_type = db.Column(db.String(80))
    complaint_category = db.Column(db.String(40))
    online_channel = db.Column(db.String(80))
    channel_detail = db.Column(db.String(80))
    complaint_text = db.Column(db.Text, nullable=False)
    complaint_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    complaint_status = db.Column(db.String(40), default="مفتوحة")
    urgency = db.Column(db.String(20), default="متوسطة")
    created_by_code = db.Column(db.String(20))
    created_by_name = db.Column(db.String(120))
    assigned_to_code = db.Column(db.String(20), db.ForeignKey("employees.employee_code"))
    assigned_to_name = db.Column(db.String(120))
    branch_code = db.Column(db.String(20), db.ForeignKey("branches.branch_code"))
    shift = db.Column(db.String(20))
    last_modified = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_escalated = db.Column(db.Boolean, default=False, index=True)
    escalated_at = db.Column(db.DateTime)
    escalated_by = db.Column(db.String(120))
    escalation_reason = db.Column(db.Text)
    escalation_recipients = db.Column(db.String(500))

    branch = db.relationship("Branch")
    details = db.relationship(
        "ComplaintDetail", back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintDetail(db.Model):
    __tablename__ = "complaint_details"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.complaint_id"))
    detail_date = db.Column(db.DateTime, default=datetime.utcnow)
    modifier = db.Column(db.String(120))
    detail_text = db.Column(db.Text)
    action_type = db.Column(db.String(40), default="note")  # note, status, created

    complaint = db.relationship(
        "Complaint",
        back_populates="details",
        order_by="ComplaintDetail.detail_date.desc()",
    )


class ComplaintType(db.Model):
    __tablename__ = "complaint_types"

    id = db.Column(db.Integer, primary_key=True)
    name_ar = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80))
    category = db.Column(db.String(40), default="delivery")
    requires_online = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def display_name(self, lang="ar"):
        if lang == "en" and self.name_en:
            return self.name_en
        return self.name_ar


class ComplaintSlaRule(db.Model):
    """Target response time (hours) per complaint type and urgency."""

    __tablename__ = "complaint_sla_rules"

    id = db.Column(db.Integer, primary_key=True)
    complaint_type = db.Column(db.String(80), nullable=True)
    urgency = db.Column(db.String(20), nullable=False)
    response_hours = db.Column(db.Integer, nullable=False, default=24)

    __table_args__ = (db.UniqueConstraint("complaint_type", "urgency"),)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(40))
    entity_id = db.Column(db.String(40))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User")


class ProductKnowledge(db.Model):
    __tablename__ = "product_knowledge"

    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), index=True)
    item_name = db.Column(db.String(200))
    active_ingredient = db.Column(db.String(200))
    medical_use = db.Column(db.Text)


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text)

    @staticmethod
    def get(key, default=None):
        row = AppSetting.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = AppSetting.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            row = AppSetting(key=key, value=value)
            db.session.add(row)
        db.session.commit()
