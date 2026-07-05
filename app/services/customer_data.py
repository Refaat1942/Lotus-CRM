"""Encrypted customer storage, search, and smart import."""
import hashlib
import json
import os
import re
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet, InvalidToken

from app.extensions import db
from app.models import Customer

PHONE_ALIASES = ("phone", "mobile", "tel", "telephone", "cell", "هاتف", "جوال", "موبايل")
FIRST_ALIASES = ("first", "firstname", "first_name", "fname", "الاسم", "الاسم الأول")
LAST_ALIASES = ("last", "lastname", "last_name", "lname", "surname", "family", "العائلة", "اسم العائلة")
NAME_ALIASES = ("name", "full", "customer", "client", "الاسم الكامل", "اسم العميل")
CITY_ALIASES = ("city", "town", "مدينة")
REGION_ALIASES = ("region", "area", "district", "governorate", "منطقة", "محافظة")


def normalize_phone(phone):
    return re.sub(r"\D", "", phone or "")


def hash_phone(phone):
    digits = normalize_phone(phone)
    if not digits:
        return None
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()


def _fernet():
    secret = os.getenv("ENCRYPTION_KEY") or os.getenv("SECRET_KEY", "lotus-crm-change-me-in-production")
    key = urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_payload(data):
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw).decode("ascii")


def decrypt_payload(token):
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError, ValueError):
        return {}


def read_customer(c):
    """Return decrypted customer fields (supports legacy plaintext rows)."""
    if not c:
        return None
    if c.enc_payload:
        data = decrypt_payload(c.enc_payload)
        return {
            "id": c.id,
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "phone_number": data.get("phone_number", ""),
            "city": data.get("city", ""),
            "region": data.get("region", ""),
        }
    return {
        "id": c.id,
        "first_name": c.first_name or "",
        "last_name": c.last_name or "",
        "phone_number": c.phone_number or "",
        "city": c.city or "",
        "region": c.region or "",
    }


def full_name(data):
    return f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()


def write_customer(c, first_name, last_name, phone_number, city="", region=""):
    phone_number = (phone_number or "").strip()
    data = {
        "first_name": (first_name or "").strip(),
        "last_name": (last_name or "").strip(),
        "phone_number": phone_number,
        "city": (city or "").strip(),
        "region": (region or "").strip(),
    }
    c.phone_hash = hash_phone(phone_number)
    c.enc_payload = encrypt_payload(data)
    c.first_name = None
    c.last_name = None
    c.phone_number = None
    c.city = None
    c.region = None
    return c


def migrate_customer_row(c):
    if c.enc_payload:
        return
    if not c.phone_number and not c.first_name:
        return
    write_customer(
        c,
        c.first_name or "",
        c.last_name or "",
        c.phone_number or "",
        c.city or "",
        c.region or "",
    )


def find_by_phone(phone):
    digits = normalize_phone(phone)
    if not digits:
        return None
    h = hash_phone(digits)
    row = Customer.query.filter_by(phone_hash=h).first()
    if row:
        return row
    return Customer.query.filter_by(phone_number=phone).first()


def mask_phone(phone, visible=4):
    digits = normalize_phone(phone)
    if not visible or len(digits) <= visible:
        return "****"
    return "*" * (len(digits) - visible) + digits[-visible:]


def customer_public_dict(c, mask=False):
    data = read_customer(c)
    if not data:
        return {"found": False}
    phone = data["phone_number"]
    return {
        "found": True,
        "id": data["id"],
        "first_name": data["first_name"],
        "last_name": data["last_name"],
        "name": full_name(data),
        "phone": mask_phone(phone) if mask else phone,
        "phone_raw": phone,
        "city": data["city"],
        "region": data["region"],
    }


def search_customers(query, limit=25):
    q = (query or "").strip()
    if not q:
        return []
    results = []
    seen = set()

    exact = find_by_phone(q)
    if exact and exact.id not in seen:
        seen.add(exact.id)
        results.append(exact)

    digits = normalize_phone(q)
    if digits and len(digits) >= 3:
        suffix = digits[-min(len(digits), 10):]
        for row in Customer.query.limit(2000).all():
            if row.id in seen:
                continue
            data = read_customer(row)
            phone_digits = normalize_phone(data["phone_number"])
            if suffix in phone_digits:
                seen.add(row.id)
                results.append(row)
                if len(results) >= limit:
                    break

    q_lower = q.lower()
    if len(q_lower) >= 2 and len(results) < limit:
        for row in Customer.query.limit(2000).all():
            if row.id in seen:
                continue
            data = read_customer(row)
            name = full_name(data).lower()
            if q_lower in name or q_lower in (data["city"] or "").lower():
                seen.add(row.id)
                results.append(row)
                if len(results) >= limit:
                    break
    return [customer_public_dict(r) for r in results[:limit]]


def _score_header(header, aliases):
    h = (header or "").strip().lower().replace("_", " ")
    for alias in aliases:
        if alias in h or h in alias:
            return 1
    return 0


def detect_column_mapping(headers):
    mapping = {}
    for idx, header in enumerate(headers):
        h = str(header or "")
        scores = {
            "phone_number": _score_header(h, PHONE_ALIASES),
            "first_name": _score_header(h, FIRST_ALIASES),
            "last_name": _score_header(h, LAST_ALIASES),
            "full_name": _score_header(h, NAME_ALIASES),
            "city": _score_header(h, CITY_ALIASES),
            "region": _score_header(h, REGION_ALIASES),
        }
        best = max(scores, key=scores.get)
        if scores[best] and best not in mapping:
            mapping[best] = idx
    return mapping


def import_rows(rows, mapping):
    """Import list-of-lists using column index mapping. Returns (added, updated, skipped)."""
    added = updated = skipped = 0
    for row in rows:
        if not row:
            skipped += 1
            continue

        def cell(field):
            idx = mapping.get(field)
            if idx is None or idx >= len(row):
                return ""
            return str(row[idx] or "").strip()

        phone = cell("phone_number")
        if not phone and mapping.get("full_name") is None:
            skipped += 1
            continue
        if not phone:
            skipped += 1
            continue

        first = cell("first_name")
        last = cell("last_name")
        if not first and not last and mapping.get("full_name") is not None:
            full = cell("full_name")
            parts = full.split(None, 1)
            first = parts[0] if parts else ""
            last = parts[1] if len(parts) > 1 else ""

        existing = find_by_phone(phone)
        if existing:
            write_customer(existing, first, last, phone, cell("city"), cell("region"))
            updated += 1
        else:
            c = Customer()
            write_customer(c, first, last, phone, cell("city"), cell("region"))
            db.session.add(c)
            added += 1
    db.session.commit()
    return added, updated, skipped


def encrypt_all_legacy_customers():
    changed = 0
    for row in Customer.query.filter(Customer.enc_payload.is_(None)).all():
        if row.phone_number or row.first_name:
            migrate_customer_row(row)
            changed += 1
    if changed:
        db.session.commit()
    return changed
