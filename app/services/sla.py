"""SLA lookup for complaint type + urgency."""
from app.models import ComplaintSlaRule
from app.services.urgency import DEFAULT_SLA_HOURS, URGENCIES


def get_sla_hours(complaint_type, urgency):
    row = ComplaintSlaRule.query.filter_by(
        complaint_type=complaint_type, urgency=urgency
    ).first()
    if row:
        return row.response_hours
    row = ComplaintSlaRule.query.filter_by(complaint_type=None, urgency=urgency).first()
    if row:
        return row.response_hours
    return DEFAULT_SLA_HOURS.get(urgency, 48)


def build_sla_matrix(complaint_types):
    """Rows for admin SLA editor: default row + each complaint type."""
    rules = {}
    for r in ComplaintSlaRule.query.all():
        key = r.complaint_type or "__default__"
        rules.setdefault(key, {})[r.urgency] = r.response_hours

    rows = [{"key": "__default__", "label_key": "sla_default_row", "name_ar": None}]
    for ct in complaint_types:
        rows.append(
            {
                "key": ct.name_ar,
                "label_key": None,
                "name_ar": ct.name_ar,
                "name_en": ct.name_en,
            }
        )

    for row in rows:
        stored = rules.get(row["key"], {})
        row["hours"] = {u: stored.get(u, DEFAULT_SLA_HOURS.get(u, 48)) for u in URGENCIES}
    return rows


def save_sla_matrix(form, complaint_types):
    from app.extensions import db

    type_keys = ["__default__"] + [ct.name_ar for ct in complaint_types]
    ComplaintSlaRule.query.delete(synchronize_session=False)
    db.session.flush()

    for key in type_keys:
        ctype = None if key == "__default__" else key
        for urgency in URGENCIES:
            field = f"sla_{key}_{urgency}"
            raw = form.get(field, "").strip()
            if not raw:
                continue
            try:
                hours = int(raw)
            except ValueError:
                continue
            if hours < 1:
                continue
            db.session.add(
                ComplaintSlaRule(
                    complaint_type=ctype,
                    urgency=urgency,
                    response_hours=hours,
                )
            )
