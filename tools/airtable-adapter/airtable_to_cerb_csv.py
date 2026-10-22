#!/usr/bin/env python3
"""
airtable_to_cerb_csv.py

Adapter: converts raw Airtable "Time Tracking" records (REST API shape, as written
by pipeline/fetch_records.py, or the {"records": [...]} response shape) into the
PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION CSV shape that build_hours_grid.py expects.
Field names are documented in airtable/AIRTABLE-SCHEMA.md.

Schema facts this adapter accounts for:
  - Hours is an Airtable 'duration' field, delivered in SECONDS, not decimal hours.
  - CERB Section is a multiple-select field with exactly one selection expected,
    formatted "<Letter><Number>: Category Name" (e.g. "A8: Design Development",
    "B14: Construction Phase - Office"), NOT the "N. Category Name" format
    build_hours_grid.py's parse_category_number() expects. This adapter extracts the
    leading integer regardless of the letter prefix.
  - "Project (linked)" is a link to Project Metadata; the REST API returns it as an
    array of bare record-ID strings. The display name is resolved through a separately
    fetched Project Metadata export (pipeline/fetch_project_metadata.py).

Exclusion rules:
  - Any row whose linked Project Metadata record has "Non-Project / Internal" checked
    is excluded outright, whether or not it has a CERB Section. That checkbox is the
    single source of truth: use it for internal buckets (vacation, admin, ...) and for
    real projects you choose to leave out (e.g. work your supervising architect can't
    sign off). This script never re-derives a reason from location or hour count.
  - Any row with NO CERB Section is excluded. The report separates internal-bucket
    rows (names in settings internal_bucket_names) from real-project rows logged
    without a category, so you can go back and categorize the latter in Airtable.
"""

import argparse
import csv
import json
import os
import re
import sys

_PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pipeline")
sys.path.insert(0, os.path.abspath(_PIPELINE_DIR))  # repo settings, under `python -I` too
try:
    from settings import internal_bucket_names  # noqa: E402
    KNOWN_NON_WORK_LABELS = internal_bucket_names()
except ImportError:  # running the adapter outside the repo layout
    KNOWN_NON_WORK_LABELS = {"VACATION", "SICK", "STAT", "ADMIN", "TEAM MEETING", "TRAINING / EVENT"}
# Used only to make the exclusion report readable -- it does NOT affect exclusion logic
# (every no-section row is excluded regardless of this list).

SECTION_RE = re.compile(r"^[A-Za-z]*(\d{1,2}):")


def extract_category_number(section_label):
    """
    Extracts the leading category number from a CERB Section label like
    'A8: Design Development' or 'C17: Buisness / Practice Management'.
    Returns None if the pattern doesn't match (caller should treat as unparsable,
    not assume it's safe to skip silently).
    """
    m = SECTION_RE.match(section_label.strip())
    if not m:
        return None
    return int(m.group(1))


def convert(records, out_csv_path, project_id_to_name, project_id_to_excluded, report_path=None):
    rows_written = 0
    excluded_flagged_non_project = []
    excluded_no_section_nonwork = []
    excluded_no_section_realproject = []
    warnings = []

    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["PROJECT", "CATEGORY", "HOURS", "NOTE DESCRIPTION"])

        for r in records:
            v = r.get("fields", {})
            rec_id = r.get("id", "<unknown>")

            project_links = v.get("Project (linked)") or []
            section_sel = v.get("CERB Section") or []
            hours_raw = v.get("Hours")
            desc = (v.get("Description") or "").strip()

            project_name = project_id_to_name.get(project_links[0]) if project_links else None
            if project_links and project_name is None:
                warnings.append(
                    f"Record {rec_id}: Project (linked) points to {project_links[0]!r}, "
                    f"which isn't in the Project Metadata export -- stale link or a stale "
                    f"export. Treated as unresolved (project_name=None)."
                )

            if len(project_links) > 1:
                warnings.append(
                    f"Record {rec_id}: {len(project_links)} Project (linked) links found "
                    f"(expected 1) -- using first ({project_name!r}), others ignored."
                )
            if len(section_sel) > 1:
                warnings.append(
                    f"Record {rec_id}: {len(section_sel)} CERB Section selections found "
                    f"(expected 1) -- using first, others ignored."
                )

            if project_links and project_id_to_excluded.get(project_links[0]):
                excluded_flagged_non_project.append({
                    "record_id": rec_id,
                    "project": project_name,
                    "hours": round((hours_raw or 0) / 3600, 2),
                    "description": desc[:100],
                })
                continue

            if not section_sel:
                # Rule: exclude every no-section row, full stop.
                bucket = (
                    excluded_no_section_nonwork
                    if (project_name is None or project_name.strip().upper() in KNOWN_NON_WORK_LABELS)
                    else excluded_no_section_realproject
                )
                bucket.append({
                    "record_id": rec_id,
                    "project": project_name,
                    "hours": round((hours_raw or 0) / 3600, 2),
                    "description": desc[:100],
                })
                continue

            section_label = section_sel[0]
            cat_num = extract_category_number(section_label)
            if cat_num is None:
                warnings.append(
                    f"Record {rec_id}: could not parse a category number from "
                    f"CERB Section label {section_label!r}. Row skipped -- needs "
                    f"manual review, not silently dropped as a non-work exclusion."
                )
                continue

            if project_name is None:
                warnings.append(
                    f"Record {rec_id}: has a CERB Section ({section_label!r}) but no "
                    f"Project selected. Row skipped -- build_hours_grid.py requires a "
                    f"project name."
                )
                continue

            if hours_raw is None or hours_raw <= 0:
                warnings.append(
                    f"Record {rec_id}: missing or non-positive Hours value "
                    f"({hours_raw!r}). Row skipped."
                )
                continue

            hours_decimal = round(hours_raw / 3600, 4)

            # CATEGORY column needs the "N. " prefix build_hours_grid.py's
            # parse_category_number() expects -- reuse the category name from the
            # source label (after the colon) for readability in the CSV.
            category_name = section_label.split(":", 1)[1].strip() if ":" in section_label else section_label
            category_field = f"{cat_num}. {category_name}"

            writer.writerow([project_name, category_field, hours_decimal, desc])
            rows_written += 1

    report = {
        "rows_written": rows_written,
        "excluded_flagged_non_project_count": len(excluded_flagged_non_project),
        "excluded_flagged_non_project_hours": round(
            sum(x["hours"] for x in excluded_flagged_non_project), 2
        ),
        "excluded_flagged_non_project_detail": excluded_flagged_non_project,
        "excluded_no_section_nonwork_count": len(excluded_no_section_nonwork),
        "excluded_no_section_nonwork_hours": round(
            sum(x["hours"] for x in excluded_no_section_nonwork), 2
        ),
        "excluded_no_section_realproject_count": len(excluded_no_section_realproject),
        "excluded_no_section_realproject_hours": round(
            sum(x["hours"] for x in excluded_no_section_realproject), 2
        ),
        "excluded_no_section_realproject_detail": excluded_no_section_realproject,
        "excluded_no_section_nonwork_detail": excluded_no_section_nonwork,
        "warnings": warnings,
    }

    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("records_json", help="Path to JSON array of Time Tracking records (raw REST 'fields' shape)")
    parser.add_argument("project_metadata_json", help="Path to JSON array of Project Metadata records "
                                                        "(pipeline/fetch_project_metadata.py output)")
    parser.add_argument("out_csv", help="Path to write the PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION CSV")
    parser.add_argument("--report", help="Path to write a JSON report of exclusions/warnings", default=None)
    args = parser.parse_args()

    with open(args.records_json, encoding="utf-8") as f:
        records = json.load(f)
    with open(args.project_metadata_json, encoding="utf-8") as f:
        project_metadata_records = json.load(f)
    # Accept both a bare list and the REST response shape {"records": [...]}.
    if isinstance(records, dict):
        records = records.get("records", [])
    if isinstance(project_metadata_records, dict):
        project_metadata_records = project_metadata_records.get("records", [])

    project_id_to_name = {
        pr["id"]: pr.get("fields", {}).get("Project Name")
        for pr in project_metadata_records
    }
    project_id_to_excluded = {
        pr["id"]: bool(pr.get("fields", {}).get("Non-Project / Internal"))
        for pr in project_metadata_records
    }

    report = convert(records, args.out_csv, project_id_to_name, project_id_to_excluded, args.report)

    print(f"Wrote {report['rows_written']} rows to {args.out_csv}", file=sys.stderr)
    print(f"Excluded (Non-Project/Internal flagged): "
          f"{report['excluded_flagged_non_project_count']} rows, "
          f"{report['excluded_flagged_non_project_hours']} hrs", file=sys.stderr)
    print(f"Excluded (no section, non-work): {report['excluded_no_section_nonwork_count']} rows, "
          f"{report['excluded_no_section_nonwork_hours']} hrs", file=sys.stderr)
    print(f"Excluded (no section, REAL PROJECT -- review these): "
          f"{report['excluded_no_section_realproject_count']} rows, "
          f"{report['excluded_no_section_realproject_hours']} hrs", file=sys.stderr)
    if report["warnings"]:
        print(f"\n{len(report['warnings'])} warning(s):", file=sys.stderr)
        for w in report["warnings"]:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
