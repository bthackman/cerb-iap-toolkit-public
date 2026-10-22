#!/usr/bin/env python3
"""
metadata_from_airtable.py

Converts the Project Metadata export (pipeline/project_metadata.json, written by
fetch_project_metadata.py -- a list of Airtable records, or the REST shape
{"records": [...]}) into the metadata.json shape generate_pdf_field_values.py reads:

    {"<Project Name>": {"location": ..., "project_type": ..., "occupancy": ...,
                        "gross_floor_area": ..., "budget": ..., "storeys": ...}, ...}

Rows with "Non-Project / Internal" checked are skipped (they never reach the form).
Blank Airtable fields are omitted, so they stay blank on the form and show up as
"missing metadata" warnings -- a typed "n/a" is kept as a real answer.
Field names follow airtable/AIRTABLE-SCHEMA.md.

    python metadata_from_airtable.py project_metadata.json metadata.json
"""

import argparse
import json
import sys

FIELD_MAP = {
    "Location": "location",
    "Project Type": "project_type",
    "Occupancy": "occupancy",
    "Gross Floor Area": "gross_floor_area",
    "Budget": "budget",
    "Number of Storeys": "storeys",
}


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, list):  # multi-select or lookup fields
        return ", ".join(str(v) for v in value if v not in (None, ""))
    if isinstance(value, dict):  # e.g. an AI/button field object -- take its text if any
        return str(value.get("value") or value.get("name") or value.get("label") or "")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def convert(records):
    """Returns (metadata dict, warnings list)."""
    if isinstance(records, dict):
        records = records.get("records", [])
    metadata = {}
    warnings = []
    for rec in records:
        fields = rec.get("fields", {})
        name = (fields.get("Project Name") or "").strip()
        if not name or fields.get("Non-Project / Internal"):
            continue
        if name in metadata:
            warnings.append("Duplicate Project Name {!r} in Project Metadata -- later row ignored.".format(name))
            continue
        entry = {}
        for airtable_field, key in FIELD_MAP.items():
            text = _as_text(fields.get(airtable_field))
            if text:
                entry[key] = text
        metadata[name] = entry
    return metadata, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project_metadata_json", help="fetch_project_metadata.py output")
    parser.add_argument("out_json", help="Where to write metadata.json")
    args = parser.parse_args()

    with open(args.project_metadata_json, encoding="utf-8") as f:
        records = json.load(f)
    metadata, warnings = convert(records)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print("Wrote metadata for {} project(s) to {}".format(len(metadata), args.out_json), file=sys.stderr)
    for w in warnings:
        print("  - " + w, file=sys.stderr)


if __name__ == "__main__":
    main()
