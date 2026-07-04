"""Sidebar navigation grouped by module."""

from flask import current_app

from app.models import SystemFunction, UserFunctionAccess

HIDDEN_ROUTES = {
    "knowledge.index",
    "complaints.branch_dashboard",
}

MENU_GROUPS = [
    ("home", "nav_group_home", 0),
    ("complaints", "nav_group_complaints", 1),
    ("customers", "nav_group_customers", 2),
    ("analytics", "nav_group_analytics", 3),
    ("administration", "nav_group_admin", 4),
]

ROUTE_TO_GROUP = {
    "main.agent_home": "home",
    "complaints.new_complaint": "complaints",
    "complaints.list_complaints": "complaints",
    "complaints.my_complaints": "complaints",
    "complaints.dashboard": "analytics",
    "customers.search": "customers",
    "customers.add": "customers",
    "reports.index": "analytics",
    "admin.live_monitor": "administration",
    "admin.index": "administration",
    "admin.audit_logs": "administration",
}


def _route_registered(route_name):
    return route_name in current_app.view_functions


def get_nav_groups(user, lang="ar"):
    if not user or not user.is_authenticated:
        return []

    rows = (
        UserFunctionAccess.query.filter_by(user_id=user.id, is_visible=True)
        .join(SystemFunction)
        .filter(SystemFunction.is_enabled == True)  # noqa: E712
        .order_by(SystemFunction.sort_order, SystemFunction.id)
        .all()
    )

    seen_routes = set()
    by_group = {g[0]: [] for g in MENU_GROUPS}

    for row in rows:
        func = row.function
        route = func.route_name
        if route in HIDDEN_ROUTES or route in seen_routes or not _route_registered(route):
            continue
        seen_routes.add(route)
        group_key = ROUTE_TO_GROUP.get(route, "complaints")
        if group_key not in by_group:
            by_group[group_key] = []
        label = func.function_name if lang == "ar" else (func.function_name_en or func.function_name)
        by_group[group_key].append(
            {
                "route_name": route,
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


def get_nav_items(user):
    groups = get_nav_groups(user)
    items = []
    for group in groups:
        items.extend(group["items"])
    return items
