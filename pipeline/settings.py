#!/usr/bin/env python3
"""
settings.py

One place for every user-adjustable setting. Reads pipeline/settings.json if it
exists (or the file named by the CERB_SETTINGS environment variable), layered on
top of pipeline/settings.example.json, layered on top of the built-in defaults
below. Keys starting with "_" are comments and are ignored.

    from settings import load_settings, repo_path, exports_dir
    s = load_settings()
    s["track"]            # "standard" or "syllabus"

Also holds the per-category minimum-hour tables for both tracks, so the
dashboard and the CERB Section suggester read the same numbers.
"""

import json
import os
from functools import lru_cache
from pathlib import Path

PIPELINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_DIR.parent
EXAMPLE_SETTINGS = PIPELINE_DIR / "settings.example.json"
LOCAL_SETTINGS = PIPELINE_DIR / "settings.json"

BUILTIN_DEFAULTS = {
    "track": "standard",
    "jurisdiction": "",
    "period_months": 6,
    "period_hours_cap": 1000,
    "backlog_cutoff_date": None,
    "backlog_text": "N/A BACKLOG HOURS",
    "internal_bucket_names": ["VACATION", "SICK", "STAT", "ADMIN", "TEAM MEETING", "TRAINING / EVENT"],
    "thin_project_hours": 10,
    "role_of_intern_header": (
        "** Refer to the attached Project Descriptions document for full project details and hours. "
        "Synopsis listed below:"
    ),
    "max_projects_per_page": 10,
    "form_pdf": "form/CERB_fillable_form.pdf",
    "exports_dir": "exports",
}

FORM_PROJECT_SLOTS = 10  # the official form has exactly 10 project columns per sheet

# ---------------------------------------------------------------------------
# Per-category minimum hours (keyed by CERB category number 1-17)
# ---------------------------------------------------------------------------
CATEGORY_NAMES = {
    1: "Programming", 2: "Site and Environmental Analysis", 3: "Schematic Design",
    4: "Engineering Systems Integration", 5: "Building Cost Analysis", 6: "Code Research",
    7: "Envelope Detailing", 8: "Design Development", 9: "Construction Documents",
    10: "Specifications and Material Research", 11: "Document Checking and Coordination",
    12: "Energy Literacy/Sustainability", 13: "Procurement and Contract Award",
    14: "Construction Phase - Office", 15: "Construction Phase - Site",
    16: "Management of the Project", 17: "Business/Practice Management",
}

# Standard IAP track -- IAP Manual 4th Ed., Appendix A (see
# skills/cerb-iap-architecture-internship/references/experience-categories.md).
STANDARD_MINIMUMS = {
    1: 80, 2: 80, 3: 240, 4: 140, 5: 80, 6: 120, 7: 80, 8: 320, 9: 760, 10: 120,
    11: 100, 12: 80, 13: 120, 14: 200, 15: 200, 16: 120, 17: 120,
}
STANDARD_TOTAL = 3720.0  # 2,960 mandatory + 760 flexible

# RAIC Syllabus Program, 2020 standard (see
# skills/cerb-iap-architecture-internship/references/syllabus-vs-standard.md).
SYLLABUS_MINIMUMS = {
    1: 210, 2: 210, 3: 630, 4: 370, 5: 210, 6: 315, 7: 210, 8: 830, 9: 2015, 10: 315,
    11: 270, 12: 210, 13: 315, 14: 530, 15: 530, 16: 315, 17: 315,
}
SYLLABUS_TOTAL = 9800.0  # 7,800 mandatory + 2,000 flexible

VALID_TRACKS = ("standard", "syllabus")


def settings_file():
    """The user's settings file: $CERB_SETTINGS if set, else pipeline/settings.json."""
    override = os.getenv("CERB_SETTINGS")
    return Path(override) if override else LOCAL_SETTINGS


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise SystemExit("Settings file {} must contain a JSON object.".format(path))
    return {k: v for k, v in data.items() if not k.startswith("_")}


@lru_cache(maxsize=1)
def load_settings():
    merged = dict(BUILTIN_DEFAULTS)
    if EXAMPLE_SETTINGS.exists():
        merged.update(_read_json(EXAMPLE_SETTINGS))
    user_file = settings_file()
    if user_file.exists():
        merged.update(_read_json(user_file))
    elif os.getenv("CERB_SETTINGS"):
        raise SystemExit("CERB_SETTINGS points to {}, which does not exist.".format(user_file))

    track = str(merged.get("track", "standard")).lower()
    if track not in VALID_TRACKS:
        raise SystemExit("Setting 'track' must be one of {} (got {!r}).".format(VALID_TRACKS, merged.get("track")))
    merged["track"] = track

    per_page = int(merged.get("max_projects_per_page") or FORM_PROJECT_SLOTS)
    if not 1 <= per_page <= FORM_PROJECT_SLOTS:
        raise SystemExit("Setting 'max_projects_per_page' must be 1-{} (the form has {} project columns).".format(
            FORM_PROJECT_SLOTS, FORM_PROJECT_SLOTS))
    merged["max_projects_per_page"] = per_page
    return merged


def get(key):
    return load_settings()[key]


def repo_path(path):
    """Resolve a settings path: absolute paths as-is, relative ones against the repo root."""
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def exports_dir():
    return repo_path(get("exports_dir"))


def form_pdf_path(override=None):
    """The fillable CERB form: an explicit override, else $CERB_FORM_PDF, else settings form_pdf."""
    return repo_path(override or os.getenv("CERB_FORM_PDF") or get("form_pdf"))


def category_targets(track=None):
    """(minimums by category number, overall total hours) for a track."""
    track = track or get("track")
    if track == "syllabus":
        return dict(SYLLABUS_MINIMUMS), SYLLABUS_TOTAL
    return dict(STANDARD_MINIMUMS), STANDARD_TOTAL


def internal_bucket_names():
    return {str(n).strip().upper() for n in get("internal_bucket_names") or []}
