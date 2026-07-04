from app.models import SystemFunction, UserFunctionAccess


def get_nav_items(user):
    if not user or not user.is_authenticated:
        return []
    rows = (
        UserFunctionAccess.query.filter_by(user_id=user.id, is_visible=True)
        .join(SystemFunction)
        .filter(SystemFunction.is_enabled == True)  # noqa: E712
        .order_by(SystemFunction.sort_order, SystemFunction.id)
        .all()
    )
    seen = set()
    items = []
    for row in rows:
        route = row.function.route_name
        if route in seen:
            continue
        seen.add(route)
        items.append(row.function)
    return items
