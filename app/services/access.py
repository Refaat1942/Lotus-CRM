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

PERMISSION_FIELDS = (
    "can_view_reports",
    "can_edit_functions",
    "can_manage_users",
    "can_export_excel",
)

ROLE_PERMISSION_DEFAULTS = {
    ROLE_AGENT: {
        "can_view_reports": False,
        "can_edit_functions": False,
        "can_manage_users": False,
        "can_export_excel": False,
    },
    ROLE_SUPERVISOR: {
        "can_view_reports": True,
        "can_edit_functions": False,
        "can_manage_users": False,
        "can_export_excel": True,
    },
    ROLE_ADMIN: {
        "can_view_reports": True,
        "can_edit_functions": True,
        "can_manage_users": True,
        "can_export_excel": True,
    },
}


def user_can_access(user, route_name):
    from app.models import SystemFunction, UserFunctionAccess

    if not user or not user.is_authenticated:
        return False

    funcs = SystemFunction.query.filter_by(route_name=route_name, is_enabled=True).all()
    if not funcs:
        return False

    if user.role == ROLE_ADMIN:
        return True

    func_ids = [f.id for f in funcs]
    access = UserFunctionAccess.query.filter(
        UserFunctionAccess.user_id == user.id,
        UserFunctionAccess.function_id.in_(func_ids),
        UserFunctionAccess.is_visible.is_(True),
    ).first()
    return access is not None


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


def get_assignable_menu_groups(functions, lang="ar"):
    """Menu items grouped for the admin permission editor."""
    from app.services.nav import HIDDEN_ROUTES, MENU_GROUPS, ROUTE_TO_GROUP

    by_group = {g[0]: [] for g in MENU_GROUPS}
    for func in functions:
        if not func.is_enabled or func.route_name in HIDDEN_ROUTES:
            continue
        group_key = ROUTE_TO_GROUP.get(func.route_name, "complaints")
        label = func.function_name if lang == "ar" else (func.function_name_en or func.function_name)
        by_group[group_key].append(
            {
                "id": func.id,
                "route_name": func.route_name,
                "icon": func.icon,
                "label": label,
                "sort_order": func.sort_order,
            }
        )

    result = []
    for group_key, label_key, _order in MENU_GROUPS:
        items = sorted(by_group.get(group_key, []), key=lambda x: x["sort_order"])
        if items:
            result.append({"key": group_key, "label_key": label_key, "items": items})
    return result


def build_role_presets(functions):
    """Role templates for the admin UI (capabilities + menu function ids)."""
    from app.services.nav import HIDDEN_ROUTES

    enabled = [f for f in functions if f.is_enabled and f.route_name not in HIDDEN_ROUTES]
    route_to_id = {f.route_name: f.id for f in enabled}
    all_ids = list(route_to_id.values())
    presets = {}
    for role, routes in ROLE_FEATURES.items():
        if routes is None:
            function_ids = all_ids
        else:
            function_ids = [route_to_id[r] for r in routes if r in route_to_id]
        presets[role] = {
            "permissions": ROLE_PERMISSION_DEFAULTS.get(role, ROLE_PERMISSION_DEFAULTS[ROLE_AGENT]),
            "functions": function_ids,
        }
    return presets


def ensure_user_permissions(user):
    from app.extensions import db
    from app.models import UserPermission

    if user.permissions:
        return user.permissions
    defaults = ROLE_PERMISSION_DEFAULTS.get(user.role or ROLE_AGENT, ROLE_PERMISSION_DEFAULTS[ROLE_AGENT])
    perms = UserPermission(user_id=user.id, **defaults)
    db.session.add(perms)
    return perms


def save_user_access(user, form, functions):
    """Save per-user capability flags and menu visibility from POST data."""
    from app.extensions import db
    from app.models import UserFunctionAccess, UserPermission
    from app.services.nav import HIDDEN_ROUTES

    perms = ensure_user_permissions(user)
    for field in PERMISSION_FIELDS:
        setattr(perms, field, field in form)

    enabled = [f for f in functions if f.is_enabled and f.route_name not in HIDDEN_ROUTES]
    route_visible = {}
    for func in enabled:
        checked = f"func_{func.id}" in form
        route_visible[func.route_name] = route_visible.get(func.route_name, False) or checked

    for func in enabled:
        visible = route_visible.get(func.route_name, False)
        row = UserFunctionAccess.query.filter_by(user_id=user.id, function_id=func.id).first()
        if row:
            row.is_visible = visible
        else:
            db.session.add(
                UserFunctionAccess(user_id=user.id, function_id=func.id, is_visible=visible)
            )
