from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship(
        "UserPermission", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    function_access = db.relationship(
        "UserFunctionAccess", back_populates="user", cascade="all, delete-orphan"
    )

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


class Employee(db.Model):
    __tablename__ = "employees"

    employee_code = db.Column(db.String(20), primary_key=True)
    employee_name = db.Column(db.String(120), nullable=False)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    phone_number = db.Column(db.String(30), unique=True, index=True)
    city = db.Column(db.String(80))
    region = db.Column(db.String(80))


class Complaint(db.Model):
    __tablename__ = "complaints"

    complaint_id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(30), nullable=False)
    complaint_type = db.Column(db.String(80))
    online_channel = db.Column(db.String(80))
    complaint_text = db.Column(db.Text, nullable=False)
    complaint_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    complaint_status = db.Column(db.String(40), default="مفتوحة")
    created_by_code = db.Column(db.String(20))
    created_by_name = db.Column(db.String(120))
    branch_code = db.Column(db.String(20), db.ForeignKey("branches.branch_code"))
    shift = db.Column(db.String(20))
    last_modified = db.Column(db.DateTime, onupdate=datetime.utcnow)

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

    complaint = db.relationship("Complaint", back_populates="details")


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
