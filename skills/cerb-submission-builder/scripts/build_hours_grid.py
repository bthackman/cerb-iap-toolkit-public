#!/usr/bin/env python3
"""
build_hours_grid.py

Computes the CERB Summary of Experience grid (17 categories x up to 10 projects)
from a raw Airtable-style export (PROJECT, CATEGORY, HOURS, NOTE DESCRIPTION).

This script is the arithmetic source of truth for the builder skill -- hour totals
and subtotals must always be computed here, never hand-tallied or estimated by the
model, per the project's explicit requirement for reliable arithmetic.

USAGE:
    python build_hours_grid.py <input.csv> [--exclude-file exclusions.json] [--out grid.json]

INPUT CSV format (header row required):
    PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION
    Maple Ridge Elementary,9. Construction Documents,42.5,"..."

CATEGORY values must start with "N. " where N is 1-17 (the leading number is parsed;
the rest of the string is ignored for grouping purposes, so minor label variations
are tolerated).

EXCLUSION FILE (optional, JSON): a list of {"project": ..., "category": ..., "hours": ...}
objects identifying rows to drop before computing the grid (used after the user has
confirmed a row is non-architectural/ineligible per writing-good-entries.md, point 7).
Matching is by exact (project, category-number, hours) triple; each entry drops at
most one row (or "count" rows if that key is given).

OUTPUT: JSON to stdout (or --out file) with the full grid, subtotals, project totals,
and grand total, plus a list of any rows that were excluded and any parsing warnings.
This output is meant to be consumed by the docx/pdf generation step, not read directly
by the end user -- render it into the actual Summary of Experience table/grid there.
"""

import argparse
import csv
import json
import sys
from collections import defaultdict

CATEGORIES = [
    (1, "A", "Programming"),
    (2, "A", "Site and Environmental Analysis"),
    (3, "A", "Schematic Design"),
    (4, "A", "Engineering Systems Integration"),
    (5, "A", "Building Cost Analysis"),
    (6, "A", "Code Research"),
    (7, "A", "Envelope Detailing"),
    (8, "A", "Design Development"),
    (9, "A", "Construction Documents"),
    (10, "A", "Specifications and Material Research"),
    (11, "A", "Document Checking and Coordination"),
    (12, "A", "Energy Literacy/Sustainability"),
    (13, "B", "Procurement and Contract Award"),
    (14, "B", "Construction Phase - Office"),
    (15, "B", "Construction Phase - Site"),
    (16, "C", "Management of the Project"),
    (17, "C", "Business/Practice Management"),
]
CATEGORY_NAME = {num: name for num, _, name in CATEGORIES}
CATEGORY_LETTER = {num: letter for num, letter, _ in CATEGORIES}

MAX_PROJECTS_PER_FORM = 10  # CERB form supports up to 10 project columns per page


def parse_category_number(raw):
    """Extract the leading integer from a CATEGORY field like '9. Construction Documents'."""
    raw = raw.strip()
    head = raw.split(".", 1)[0].strip()
    try:
        num = int(head)
    except ValueError:
        return None
    if num not in CATEGORY_NAME:
        return None
    return num


def load_rows(csv_path):
    rows = []
    warnings = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"PROJECT", "CATEGORY", "HOURS", "NOTE DESCRIPTION"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Input CSV missing required column(s): {sorted(missing)}")
        for i, r in enumerate(reader, start=2):  # row 1 is header
            project = (r["PROJECT"] or "").strip()
            category_raw = (r["CATEGORY"] or "").strip()
            hours_raw = (r["HOURS"] or "").strip()
            note = (r["NOTE DESCRIPTION"] or "").strip()

            if not project or not category_raw or not hours_raw:
                warnings.append(f"Row {i}: skipped, missing PROJECT/CATEGORY/HOURS.")
                continue

            cat_num = parse_category_number(category_raw)
            if cat_num is None:
                warnings.append(
                    f"Row {i}: could not parse a valid category number (1-17) from "
                    f"'{category_raw}'. Row skipped -- needs manual categorization."
                )
                continue

            try:
                hours = float(hours_raw)
            except ValueError:
                warnings.append(f"Row {i}: could not parse HOURS value '{hours_raw}'. Row skipped.")
                continue

            if hours <= 0:
                warnings.append(f"Row {i}: non-positive hours ({hours}) for {project}. Row skipped.")
                continue

            rows.append({
                "project": project,
                "category": cat_num,
                "hours": hours,
                "note": note,
                "_source_row": i,
            })
    return rows, warnings


def apply_exclusions(rows, exclusions):
    """Drop rows matched by exclusion entries. Each entry consumes at most one row
    (or `count` rows if the entry carries a "count" key), so two identical
    (project, category, hours) rows are not both dropped by a single entry."""
    if not exclusions:
        return rows, []
    remaining = [int(e.get("count", 1)) for e in exclusions]
    excluded = []
    kept = []
    for r in rows:
        idx = next(
            (
                i for i, e in enumerate(exclusions)
                if remaining[i] > 0
                and e.get("project") == r["project"]
                and int(e.get("category")) == r["category"]
                and abs(float(e.get("hours")) - r["hours"]) < 1e-6
            ),
            None,
        )
        if idx is not None:
            remaining[idx] -= 1
            excluded.append(r)
        else:
            kept.append(r)
    return kept, excluded


def build_grid(rows):
    projects_in_order = []
    for r in rows:
        if r["project"] not in projects_in_order:
            projects_in_order.append(r["project"])

    if len(projects_in_order) > MAX_PROJECTS_PER_FORM:
        raise SystemExit(
            f"{len(projects_in_order)} distinct projects found, but the CERB form supports "
            f"only {MAX_PROJECTS_PER_FORM} project columns per page. Split into multiple "
            f"submission pages (renumbering projects 11, 12, 13... per the manual's "
            f"instructions) before generating the form -- run "
            f"tools/airtable-adapter/split_multipage.py first (pipeline/run_period.py prepare "
            f"does this automatically)."
        )

    project_col = {name: i + 1 for i, name in enumerate(projects_in_order)}
    grid = defaultdict(lambda: defaultdict(float))
    for r in rows:
        col = project_col[r["project"]]
        grid[r["category"]][col] += r["hours"]

    subtotals = {"A": 0.0, "B": 0.0, "C": 0.0}
    project_totals = defaultdict(float)
    category_rows = []

    for num, letter, name in CATEGORIES:
        per_project = {col: round(grid[num].get(col, 0.0), 2) for col in range(1, len(projects_in_order) + 1)}
        row_total = round(sum(per_project.values()), 2)
        subtotals[letter] += row_total
        for col, h in per_project.items():
            project_totals[col] += h
        category_rows.append({
            "category_number": num,
            "category_name": name,
            "section": letter,
            "hours_by_project_column": per_project,
            "row_total": row_total,
        })

    grand_total = round(sum(subtotals.values()), 2)
    subtotals = {k: round(v, 2) for k, v in subtotals.items()}
    project_totals = {col: round(v, 2) for col, v in project_totals.items()}

    return {
        "projects": [{"column": i + 1, "name": name} for i, name in enumerate(projects_in_order)],
        "category_rows": category_rows,
        "subtotals": subtotals,
        "project_totals": project_totals,
        "grand_total": grand_total,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_csv", help="Path to the raw hours export CSV")
    parser.add_argument("--exclude-file", help="Path to a JSON file listing rows to exclude", default=None)
    parser.add_argument("--out", help="Write JSON output to this path instead of stdout", default=None)
    args = parser.parse_args()

    rows, warnings = load_rows(args.input_csv)

    exclusions = []
    if args.exclude_file:
        with open(args.exclude_file, encoding="utf-8") as f:
            exclusions = json.load(f)

    kept_rows, excluded_rows = apply_exclusions(rows, exclusions)
    result = build_grid(kept_rows)
    result["warnings"] = warnings
    result["excluded_rows"] = [
        {"project": r["project"], "category": r["category"], "category_name": CATEGORY_NAME[r["category"]],
         "hours": r["hours"], "note": r["note"]}
        for r in excluded_rows
    ]
    result["row_count_used"] = len(kept_rows)
    result["row_count_excluded"] = len(excluded_rows)

    output_text = json.dumps(result, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"Wrote grid JSON to {args.out}", file=sys.stderr)
    else:
        print(output_text)

    if warnings:
        print(f"\n{len(warnings)} warning(s) -- see 'warnings' in output.", file=sys.stderr)


if __name__ == "__main__":
    main()
