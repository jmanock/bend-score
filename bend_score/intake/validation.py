from __future__ import annotations

from urllib.parse import urlparse


SUPPORTED_SOURCES = {
    "flippa": "Flippa",
    "acquire": "Acquire",
    "acquire.com": "Acquire",
    "microns": "Microns",
    "empire flippers": "Empire Flippers",
    "fe international": "FE International",
    "motion invest": "Motion Invest",
    "manual": "Manual",
    "other": "Other",
}


def normalize_source(value: str | None) -> str:
    if not value or not value.strip():
        return "Manual"
    return SUPPORTED_SOURCES.get(value.strip().lower(), "Other")


def parse_number(value: object, field_name: str) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    cleaned = str(value).strip().replace("$", "").replace(",", "")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be numeric if provided.") from exc


def parse_int(value: object, field_name: str) -> int:
    return int(parse_number(value, field_name))


def validate_url(value: str | None) -> str:
    if not value or not value.strip():
        return ""
    url = value.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must start with http:// or https:// when provided.")
    return url

