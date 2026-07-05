"""Complaint category hierarchy and channel options."""

CATEGORIES = [
    ("cash", "category_cash"),
    ("insurance", "category_insurance"),
    ("delivery", "category_delivery"),
    ("digital", "category_digital"),
    ("online", "category_online"),
]

DIGITAL_PLATFORMS = ["Instashop", "Talabat", "Chefaa", "Vezeeta"]
ONLINE_SOURCES = ["Application", "Website"]

CATEGORY_KEYS = {key for key, _ in CATEGORIES}


def category_label_key(category_key):
    for key, label in CATEGORIES:
        if key == category_key:
            return label
    return category_key
