from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup


_DIGIT_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(K)?", re.IGNORECASE)
_EXPERIENCE_PATTERNS: Iterable[tuple[str, str]] = (
    (r"\bstage|internship\b", "Internship"),
    (r"\b(apprenti|alternance)\b", "Apprenticeship"),
    (r"\b(junior|0[-–]2\s*(ans|years)|entry level)\b", "Junior"),
    (r"\b(3[-–]5\s*(ans|years)|mid[- ]level)\b", "Mid"),
    (r"\b(6\+\s*(ans|years)|senior|lead)\b", "Senior"),
)
_EDUCATION_PATTERNS: Iterable[tuple[str, str]] = (
    (r"bac\+5|master|msc|maitrise", "Master"),
    (r"bac\+4|licence|bachelor", "Bachelor"),
    (r"bac\+3", "Bachelor"),
    (r"bac\+2|associate", "Associate"),
    (r"doctorat|phd", "Doctorate"),
)
_REQUIREMENT_SECTION_PATTERN = re.compile(
    r"(?P<section>(profil|responsabilit[eé]s|missions|requirements|qualifications)[^\n:]{0,40}:?)(?P<body>.*?)(?:\n{2,}|$)",
    re.IGNORECASE | re.DOTALL,
)
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def to_digit(value: str | None) -> int | None:

    if not value:
        return None

    match = _DIGIT_PATTERN.search(value)
    if not match:
        return None

    number = float(match.group(1).replace(",", "."))
    if match.group(2):
        number *= 1000
    return int(number)


def clean_html(value: str | None) -> str | None:

    if not value:
        return None

    text = BeautifulSoup(value, "html.parser").get_text("\n", strip=True)
    text = re.sub(r"\r", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    normalized = text.strip()
    return normalized or None


def extract_experience_level(text: str | None) -> str | None:
    if not text:
        return None

    lower = text.lower()
    for pattern, label in _EXPERIENCE_PATTERNS:
        if re.search(pattern, lower):
            return label
    return None


def extract_education_level(text: str | None) -> str | None:
    if not text:
        return None

    lower = text.lower()
    for pattern, label in _EDUCATION_PATTERNS:
        if re.search(pattern, lower):
            return label
    return None


def extract_requirements_snippet(text: str | None) -> str | None:
    if not text:
        return None

    section_match = _REQUIREMENT_SECTION_PATTERN.search(text)
    if section_match:
        body = section_match.group("body").strip()
        return body[:600]

    lines = [line.strip("-• ") for line in text.splitlines() if line.strip()]
    bullet_lines = [
        line
        for line in lines
        if len(line) < 200
        and any(
            word in line.lower() for word in ("respons", "requ", "compétence", "skill")
        )
    ]
    if bullet_lines:
        return "; ".join(bullet_lines[:6])

    return None


def normalize_date(value: str | None) -> str | None:

    if not value:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    if trimmed.endswith("Z"):
        trimmed = trimmed[:-1] + "+00:00"

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(trimmed, fmt)
            return dt.date().isoformat()
        except ValueError:
            continue

    match = re.search(r"(\d{4}-\d{2}-\d{2})", trimmed)
    if match:
        return match.group(1)

    return trimmed
