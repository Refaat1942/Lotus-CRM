"""Complaint urgency levels and default SLA hours."""

URGENCIES = ["ضعيفة", "متوسطة", "عالية", "فورية"]
URGENCY_DEFAULT = "متوسطة"
URGENCY_IMMEDIATE = "فورية"

DEFAULT_SLA_HOURS = {
    "ضعيفة": 72,
    "متوسطة": 48,
    "عالية": 24,
    "فورية": 4,
}
