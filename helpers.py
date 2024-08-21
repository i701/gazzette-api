"""Helper functions for the Gazette API."""

from datetime import datetime
import re
from constants import MONTH_TRANSLATIONS


def detect_component(part):
    """Detect if the part is a day, month, year, or time."""
    if re.match(r"^\d{1,2}$", part):
        return "day"
    elif re.match(r"^\d{4}$", part):
        return "year"
    elif re.match(r"^\d{2}:\d{2}$", part):
        return "time"
    elif part in MONTH_TRANSLATIONS:
        return "month"
    return "unknown"


def maldivian_to_iso(date_str):
    """Convert a maldivian date string to ISO 8601."""
    parts = date_str.split()

    day = None
    month = None
    year = None
    time_str = None

    for part in parts:
        component_type = detect_component(part)
        if component_type == "day":
            day = part
        elif component_type == "month":
            month = MONTH_TRANSLATIONS.get(part, "Unknown")
        elif component_type == "year":
            year = part
        elif component_type == "time":
            time_str = part

    if day is None or month is None or year is None:
        raise ValueError("Date string is missing required components")

    if time_str is None:
        time_str = "00:00"

    date_formatted = f"{month} {day}, {year} {time_str}"

    try:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y %H:%M")
    except ValueError:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y")

    iso_date = dt_obj.isoformat()

    return iso_date
