#!/usr/bin/env python3
"""
validate_entries.py

Deterministic pre-write validation for cerb-airtable-logger. This is the arithmetic/
schema-conformance gate -- it never makes a judgment call about what a value *should*
be (that's the skill's job, upstream); it only checks that the staged payload is
internally consistent and byte-exact against the live Airtable schema before anything
is written. Run this after step 8 (user has answered all ambiguities) and before step 11
(the actual write) of SKILL.md. Stop on any error -- never write a payload this script
flags.

USAGE:
    python validate_entries.py <entries.json> <schema.json> [--out report.json]

ENTRIES JSON: a list of staged entry objects, each shaped:
    {
        "date": "YYYY-MM-DD",
        "project_resolved": "Community Library Renovation",
        "hours_decimal": 1.5,
        "hours_seconds": 5400,
        "description": "1.5 Hr - Community Library Renovation - ...",
        "cerb_section": "A9: Construction Documents" | null
    }
Use this same shape for every staged chunk file so parsing, suggestion and validation
steps can hand files to each other unchanged.

SCHEMA JSON: the live valid-value lists, fetched fresh in SKILL.md step 1 and saved as:
    {"project_choices": ["Community Library Renovation", "ADMIN", ...],
     "cerb_section_choices": ["A9: Construction Documents", ...]}
project_choices comes from the Project Metadata table's `Project Name` values;
cerb_section_choices from the Time Tracking table's `CERB Section` options (see
airtable/AIRTABLE-SCHEMA.md). Never hand-type this file from memory -- it must come from
the live fetch made in SKILL.md step 1, so it reflects projects added since this script
was last used.

OUTPUT: JSON to stdout (or --out file) with {"valid": bool, "errors": [...], "warnings": [...]}.
A non-empty "errors" list means the payload must not be written as-is.
"""

import argparse
import json
import re
import sys
from datetime import date

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_REASONABLE_HOURS = 8.0
QUARTER_HOUR_SECONDS = 900  # 0.25 Hr


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_date(entry, errors):
    d = entry.get("date", "")
    if not DATE_RE.match(d):
        errors.append(f"{entry.get('description', '<no description>')[:60]}: "
                       f"date '{d}' is not ISO YYYY-MM-DD.")
        return
    try:
        date.fromisoformat(d)
    except ValueError:
        errors.append(f"{entry.get('description', '<no description>')[:60]}: "
                       f"date '{d}' does not parse as a real calendar date.")


def validate_hours(entry, warnings, errors):
    decimal = entry.get("hours_decimal")
    seconds = entry.get("hours_seconds")
    if decimal is None or seconds is None:
        errors.append(f"{entry.get('date')}: missing hours_decimal or hours_seconds.")
        return

    if seconds != round(decimal * 3600):
        errors.append(
            f"{entry.get('date')}: hours_seconds ({seconds}) does not match "
            f"hours_decimal ({decimal}) * 3600 = {round(decimal * 3600)}."
        )

    if decimal <= 0:
        errors.append(f"{entry.get('date')}: non-positive hours ({decimal}).")

    if decimal > MAX_REASONABLE_HOURS:
        warnings.append(
            f"{entry.get('date')}: {decimal} Hr exceeds the {MAX_REASONABLE_HOURS} Hr "
            f"sanity bound -- confirm this isn't a parsing error before writing."
        )

    if seconds % QUARTER_HOUR_SECONDS != 0:
        warnings.append(
            f"{entry.get('date')}: {decimal} Hr is not a quarter-hour multiple -- "
            f"every entry in the historical data lands on a quarter-hour; double-check "
            f"this wasn't misparsed."
        )


def validate_project(entry, project_choices, errors):
    project = entry.get("project_resolved")
    if not project:
        errors.append(f"{entry.get('date')}: project_resolved is empty -- entry was not "
                       f"actually resolved before validation.")
        return
    if project not in project_choices:
        errors.append(
            f"{entry.get('date')}: project '{project}' is not a byte-exact match to any "
            f"live Project choice. Check for a typo or missing new-choice confirmation."
        )


def validate_cerb_section(entry, cerb_section_choices, warnings, errors):
    section = entry.get("cerb_section")
    if section is None:
        return  # blank is a valid, common state -- see SKILL.md step 5
    if section not in cerb_section_choices:
        errors.append(
            f"{entry.get('date')}: cerb_section '{section}' is not a byte-exact match to "
            f"any live CERB Section choice -- check for a typo (choice names contain "
            f"intentional typos like 'Buisness'/'Enviromental' that must match exactly)."
        )


def validate_description(entry, warnings):
    desc = entry.get("description", "")
    project = entry.get("project_resolved", "")
    decimal = entry.get("hours_decimal")
    if decimal is None:
        return
    expected_prefix = f"{decimal} Hr - {project}"
    # Tolerate "2.0" vs "2" formatting differences; just check the numeric+project pairing appears.
    if project and project not in desc:
        warnings.append(
            f"{entry.get('date')}: description does not contain the resolved project name "
            f"'{project}' -- check the Description was built from the canonical name, not "
            f"the raw input mention."
        )


def validate_entries(entries, schema):
    errors = []
    warnings = []
    project_choices = set(schema.get("project_choices", []))
    cerb_section_choices = set(schema.get("cerb_section_choices", []))

    if not project_choices:
        errors.append("Schema file has no project_choices -- did you pass a real "
                       "get_table_schema export, not a placeholder?")

    for entry in entries:
        validate_date(entry, errors)
        validate_hours(entry, warnings, errors)
        validate_project(entry, project_choices, errors)
        validate_cerb_section(entry, cerb_section_choices, warnings, errors)
        validate_description(entry, warnings)

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings,
            "entry_count": len(entries)}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entries_json", help="Path to staged entries JSON (list of entry objects)")
    parser.add_argument("schema_json", help="Path to live schema JSON (project_choices, cerb_section_choices)")
    parser.add_argument("--out", help="Write report JSON to this file instead of stdout")
    args = parser.parse_args()

    entries = load_json(args.entries_json)
    schema = load_json(args.schema_json)

    if not isinstance(entries, list):
        raise SystemExit("entries_json must be a JSON list of entry objects.")

    report = validate_entries(entries, schema)
    output = json.dumps(report, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)

    sys.exit(0 if report["valid"] else 1)


if __name__ == "__main__":
    main()
