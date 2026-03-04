from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from bs4 import BeautifulSoup


_DIGIT_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(K)?", re.IGNORECASE)
_Indeed_EXPERIENCE_PATTERNS: Iterable[tuple[str, str]] = (
    (r"\b(stage|internship)\b", "Internship"),
    (r"\b(apprenti|alternance)\b", "Internship"),
    (r"\b(junior|0[-–]2\s*(ans|years)|entry level)\b", "Junior"),
    (r"\b(3[-–]5\s*(ans|years)|mid[- ]level)\b", "Mid"),
    (r"\b(6\+\s*(ans|years)|senior|lead)\b", "Senior"),
)
_Indeed_EDUCATION_PATTERNS: Iterable[tuple[str, str]] = (
    (r"bac\+5|master|msc|maitrise", "Master"),
    (r"bac\+4|licence|bachelor", "Bachelor"),
    (r"bac\+3", "Bachelor"),
    (r"bac\+2|associate", "Associate"),
    (r"doctorat|phd", "Doctorate"),
)
_Indeed_REQUIREMENT_SECTION_PATTERN = re.compile(
    r"^[ \t]*(?P<section>"
    r"(?:profil|responsabilit[eé]s|missions|requirements?|qualifications?"
    r"|nous (?:cherchons|recherchons|recrutons)"
    r"|qui (?:\u00eates|\u00eatiez|etes)-vous"
    r"|votre (?:profil|exp[eé]rience|parcours)"
    r"|vos comp[eé]tences"
    r"|ce que nous (?:recherchons|attendons)"
    r"|exp[eé]riences? requises?"
    r"|comp[eé]tences? (?:requises?|cl[eé]s?|techniques?)"
    r"|must[- ]have"
    r"|about you"
    r"|what (?:we(?:'re| are) looking for|you(?:'ll)? (?:bring|need|have))"
    r"|your background"
    r"|ideal candidate"
    r"|(?:key )?requirements? (?:include|for)"
    r"|experience(?:s)? required"
    r")"
    r"[^\n:]{0,40}:?)(?P<body>.*?)(?:\n{2,}|$)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)
_LINKEDIN_REQUIREMENT_SECTION_PATTERN = re.compile(
    r"^[ \t]*(?P<section>"
    r"(?:about you"
    r"|what you(?:'ll| will) (?:bring|need|have)"
    r"|the ideal candidate(?: profile)?"
    r"|your (?:profile|background)"
    r"|nous (?:recherchons|recrutons)"
    r"|le (?:profil|candidat) id[eé]al"
    r"|votre profil"
    r"|ce que vous apportez"
    r")"
    r"[ \t]{0,10}:?[ \t]*)\n(?P<body>.*?)(?:\n{2,}|\Z)",
    re.IGNORECASE | re.DOTALL | re.MULTILINE,
)
_BULLET_START = re.compile(r"^[-•*·]|\d+[.)]\s")
_SIGNAL_WORDS = (
    # English
    "respons", "requ", "skill", "experi", "certif", "technolog",
    "programm", "framework", "language", "qualif", "background",
    "develop", "python", "java", "sql", "aws", "azure",
    "react", "node", "docker", "git", "api", "data", "machine",
    # French
    "compétence", "expéri", "connaissance", "maîtris", "maitris",
    "formation", "diplôm", "diplom", "cherch", "recrut", "profil",
    "outil", "logiciel", "environnement",
)
# Matches the start of a section that signals the end of the requirements block.
_STOP_SECTION_PATTERN = re.compile(
    r"\n[ \t]*(?:hiring[ \t]+process|nice[- \t]to[- \t]have|what[ \t]+we[ \t]+offer"
    r"|location\b|benefits\b|about[ \t]+(?:the[ \t]+)?(?:company|us)\b)",
    re.IGNORECASE,
)
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)

_WTTJ_EXPERIENCE_MAP: dict[str, str] = {
    "LESS_THAN_6_MONTHS": "Internship",
    "NO_EXPERIENCE": "Junior",
    "1_TO_2_YEARS": "Junior",
    "2_TO_3_YEARS": "Mid",
    "3_TO_4_YEARS": "Mid",
    "4_TO_5_YEARS": "Senior",
    "5_TO_7_YEARS": "Senior",
    "7_TO_10_YEARS": "Lead",
    "MORE_THAN_10_YEARS": "Lead",
}

_WTTJ_EDUCATION_MAP: dict[str, str] = {
    "bac_2": "Associate",
    "bac_3": "Bachelor",
    "bac_4": "Bachelor",
    "bac_5": "Master",
    "bac_6": "Master",
    "bac_8": "Doctorate",
}

_LinkedIn_EXPERIENCE_MAP: dict[str, str] = {
    # English labels
    "internship": "Internship",
    "entry level": "Junior",
    "associate": "Junior",
    "mid-senior level": "Senior",
    "director": "Senior",      # was "Lead" — aligned to Indeed vocabulary
    "executive": "Senior",     # was "Lead" — aligned to Indeed vocabulary
    # French labels
    "stage": "Internship",
    "alternance": "Internship",
    "débutant": "Junior",
    "expérimenté": "Senior",
    "directeur": "Senior",
    "cadre dirigeant": "Senior",
}

_LinkedIn_CONTRACT_MAP: dict[str, str] = {
    # English
    "internship": "internship",
    "full-time": "full_time",
    "part-time": "part_time",
    "contract": "contractor",
    "temporary": "temporary",
    "volunteer": "volunteer",
    "other": "other",
    # French
    "stage": "internship",
    "alternance": "internship",
    "cdi": "full_time",
    "temps plein": "full_time",
    "cdd": "temporary",
    "temps partiel": "part_time",
    "freelance/indépendant": "contractor",
    "freelance": "contractor",
    "autre": "other",
}


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

    return normalize_experience_level(text)


def extract_contract_type(list: list[str] | None) -> str | None:
    if not list:
        return None
    return list[0].lower()


def normalize_linkedin_contract(value: str | None) -> str | None:
    if not value:
        return None
    return _LinkedIn_CONTRACT_MAP.get(value.strip().lower())


def extract_education_level(text: str | None) -> str | None:
    if not text:
        return None

    return normalize_education_level(text)


def normalize_experience_level(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized or normalized.lower() in {"not specified", "non spécifié"}:
        return None

    enum_key = normalized.upper()
    if enum_key in _WTTJ_EXPERIENCE_MAP:
        return _WTTJ_EXPERIENCE_MAP[enum_key]

    label_key = normalized.lower()
    if label_key in _LinkedIn_EXPERIENCE_MAP:      # LinkedIn structured labels
        return _LinkedIn_EXPERIENCE_MAP[label_key]

    if label_key in {"internship", "apprenticeship", "junior", "mid", "senior", "lead"}:
        return label_key.title()

    for pattern, label in _Indeed_EXPERIENCE_PATTERNS:
        if re.search(pattern, label_key):
            return label

    return None


def normalize_education_level(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized or normalized.lower() in {"not specified", "non spécifié"}:
        return None

    enum_key = normalized.lower()
    if enum_key in _WTTJ_EDUCATION_MAP:
        return _WTTJ_EDUCATION_MAP[enum_key]

    if enum_key in {"associate", "bachelor", "master", "doctorate"}:
        return enum_key.title()

    lower = normalized.lower()
    for pattern, label in _Indeed_EDUCATION_PATTERNS:
        if re.search(pattern, lower):
            return label
    return None


_DUTY_HEADERS = frozenset({"responsabilit", "mission"})


def extract_requirements_snippet(text: str | None) -> str | None:
    if not text:
        return None

    # Stage 1a: Indeed / WTTJ section headers.
    # Use finditer to try every match and skip duty-only sections (missions,
    # responsabilités) that precede the actual requirements block.
    # Body is extracted manually from match.end() because the regex body group
    # is unreliable in MULTILINE mode ($ matches at every line-end).
    for section_match in _Indeed_REQUIREMENT_SECTION_PATTERN.finditer(text):
        header = section_match.group("section").lower().strip().rstrip(": ")
        if any(header.startswith(dh) for dh in _DUTY_HEADERS):
            continue
        after = text[section_match.end():]
        para_break = re.search(r"\n{2,}", after)
        body = (after[: para_break.start()] if para_break else after).strip()
        if body:
            stop = _STOP_SECTION_PATTERN.search(body)
            if stop:
                body = body[: stop.start()].strip()
        if body:
            return body[:600]

    # Stage 1b: LinkedIn section headers
    linkedin_match = _LINKEDIN_REQUIREMENT_SECTION_PATTERN.search(text)
    if linkedin_match:
        body = linkedin_match.group("body").strip()
        stop = _STOP_SECTION_PATTERN.search(body)
        if stop:
            body = body[:stop.start()].strip()
        if body:
            return body[:600]

    # Stage 1.5: density-scored paragraph (no heading present).
    # Require signal_hits / lines >= 0.4 to reject long company-intro paragraphs
    # that accumulate signal words simply by being large.
    best_score = 0.0
    best_para: str | None = None
    for para in re.split(r"\n{2,}", text):
        para_lines = [l.strip() for l in para.splitlines() if l.strip()]
        if not para_lines:
            continue
        signal_hits = sum(
            1 for line in para_lines for word in _SIGNAL_WORDS if word in line.lower()
        )
        bullet_count = sum(1 for line in para_lines if _BULLET_START.match(line))
        score = signal_hits + 0.5 * bullet_count
        density = signal_hits / len(para_lines)
        if score > best_score and density >= 0.4:
            best_score = score
            best_para = para.strip()
    if best_score >= 2 and best_para:
        return best_para[:600]

    lines = [line.strip("-• \t") for line in text.splitlines() if line.strip()]
    bullet_lines = [
        line
        for line in lines
        if len(line) < 400
        and any(word in line.lower() for word in _SIGNAL_WORDS)
    ]
    if bullet_lines:
        return "; ".join(bullet_lines[:8])

    # Stage 3: largest contiguous bullet cluster
    _BULLET_RE = re.compile(r"^[-•*·]|\d+[.)]\s")
    current: list[str] = []
    best: list[str] = []
    for line in lines:
        if _BULLET_RE.match(line):
            current.append(line.lstrip("-•*· ").strip())
        else:
            if len(current) > len(best):
                best = current
            current = []
    if len(current) > len(best):
        best = current
    if len(best) >= 3:
        return "; ".join(best[:8])

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


_LINKEDIN_RELATIVE_DATE_RE = re.compile(
    r'(\d+)[\s\xa0]*(minute|hour|heure|day|jour|week|semaine|month|mois)s?',
    re.IGNORECASE,
)
_FR_UNIT_MAP = {'heure': 'hour', 'jour': 'day', 'semaine': 'week', 'mois': 'month'}

def parse_linkedin_date(text: str | None) -> str | None:
    """Convert a LinkedIn relative date string to YYYY-MM-DD.

    Handles English ('X weeks ago') and French ('il y a X semaines').
    Returns None if the text cannot be parsed.
    """
    if not text:
        return None
    match = _LINKEDIN_RELATIVE_DATE_RE.search(text.strip())
    if not match:
        return None
    n, unit = int(match.group(1)), match.group(2).lower()
    unit = _FR_UNIT_MAP.get(unit, unit)
    from datetime import timedelta
    if unit in ('minute', 'hour'):
        delta = timedelta(days=0)
    elif unit == 'day':
        delta = timedelta(days=n)
    elif unit == 'week':
        delta = timedelta(weeks=n)
    else:  # month
        delta = timedelta(days=n * 30)
    return (datetime.today().date() - delta).isoformat()
