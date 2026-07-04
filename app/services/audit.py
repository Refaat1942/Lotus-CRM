from datetime import datetime

from flask import request
from flask_login import current_user

from app.extensions import db


def log_action(action, entity_type=None, entity_id=None, details=None, user=None):
    from app.models import AuditLog

    u = user or (current_user if current_user.is_authenticated else None)
    entry = AuditLog(
        user_id=u.id if u else None,
        username=u.username if u else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details,
        ip_address=request.remote_addr if request else None,
    )
    db.session.add(entry)
