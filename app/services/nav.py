from app.models import SystemFunction, UserFunctionAccess


def get_nav_items(user):
    if not user or not user.is_authenticated:
        return []
    rows = (
        UserFunctionAccess.query.filter_by(user_id=user.id, is_visible=True)
        .join(SystemFunction)
        .filter(SystemFunction.is_enabled == True)  # noqa: E712
        .order_by(SystemFunction.sort_order)
        .all()
    )
    return [row.function for row in rows]
