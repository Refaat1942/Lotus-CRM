"""Unified feature access and role presets for call center agents."""

ROLE_AGENT = "agent"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMIN = "admin"

ROLE_FEATURES = {
    ROLE_AGENT: [
        "main.agent_home",
        "complaints.new_complaint",
        "complaints.list_complaints",
        "complaints.my_complaints",
        "customers.search",
        "customers.add",
    ],
    ROLE_SUPERVISOR: [
        "main.agent_home",
        "complaints.new_complaint",
        "complaints.list_complaints",
        "complaints.my_complaints",
        "customers.search",
        "customers.add",
        "complaints.dashboard",
        "reports.index",
    ],
    ROLE_ADMIN: None,  # all enabled features
}


def user_can_access(user, route_name):
    from app.models import SystemFunction, UserFunctionAccess

    if not user or not user.is_authenticated:
        return False
    func = SystemFunction.query.filter_by(route_name=route_name, is_enabled=True).first()
    if not func:
        return False
    access = UserFunctionAccess.query.filter_by(user_id=user.id, function_id=func.id).first()
    return bool(access and access.is_visible)


def user_can_view_reports(user):
    return user.permissions and user.permissions.can_view_reports and user_can_access(
        user, "reports.index"
    )


ROLE_DESCRIPTIONS = {
    ROLE_AGENT: "role_agent_desc",
    ROLE_SUPERVISOR: "role_supervisor_desc",
    ROLE_ADMIN: "role_admin_desc",
}


def user_can_admin(user):
    return user.permissions and user.permissions.can_manage_users and user_can_access(
        user, "admin.index"
    )


def apply_role_features(user, role):
    from app.extensions import db
    from app.models import SystemFunction, UserFunctionAccess

    allowed = ROLE_FEATURES.get(role)
    for func in SystemFunction.query.filter_by(is_enabled=True).all():
        visible = True if allowed is None else func.route_name in allowed
        row = UserFunctionAccess.query.filter_by(user_id=user.id, function_id=func.id).first()
        if row:
            row.is_visible = visible
        else:
            db.session.add(
                UserFunctionAccess(user_id=user.id, function_id=func.id, is_visible=visible)
            )


def sync_new_functions_to_users():
    """Grant new system functions to users based on their role."""
    from app.extensions import db
    from app.models import SystemFunction, User, UserFunctionAccess

    for user in User.query.all():
        role = user.role or ROLE_AGENT
        allowed = ROLE_FEATURES.get(role)
        for func in SystemFunction.query.filter_by(is_enabled=True).all():
            exists = UserFunctionAccess.query.filter_by(
                user_id=user.id, function_id=func.id
            ).first()
            if not exists:
                visible = True if allowed is None else func.route_name in allowed
                db.session.add(
                    UserFunctionAccess(user_id=user.id, function_id=func.id, is_visible=visible)
                )
    db.session.commit()
