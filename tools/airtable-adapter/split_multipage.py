#!/usr/bin/env python3
"""
split_multipage.py

Splits a raw PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION CSV into multiple page-sized
CSVs (<=10 distinct projects each) when the form's 10-project-per-page limit is
exceeded, per the IAP manual's own instruction: "add extra sheets if more,
renumbering 11, 12, 13...".

This is a thin wrapper around build_hours_grid.py, NOT a modification of it --
the verified arithmetic core (build_hours_grid.py) is run independently, once per
page, on its own already-small (<=10 project) slice. This script's only job is:
  1. Determine project ordering (caller-specified; the pipeline default is
     largest-hours-first).
  2. Split the raw rows into page-sized chunks along project boundaries (a single
     project's rows are never split across pages).
  3. Write one CSV per page, with rows grouped in the page's project order --
     build_hours_grid.py assigns columns by first appearance, so the CSV's row order
     IS the column order (writing rows in their original order silently discarded
     largest-hours-first).
  4. After build_hours_grid.py is run on each page CSV independently, renumber
     page 2+'s internal project columns to continue from page 1's count (e.g.
     page 2's column 1 becomes "project 11" for PDF-filling / display purposes --
     this script provides that renumbering map in the manifest; it does not call
     build_hours_grid.py itself. Pass the manifest to generate_pdf_field_values.py
     via --manifest/--page, which applies the map).

USAGE:
    python split_multipage.py <input.csv> [--max-per-page 10] --order largest_hours_first --out-prefix page

--max-per-page defaults to max_projects_per_page in pipeline/settings.json (10, the
form's column count). Writes <out-prefix>_1.csv, <out-prefix>_2.csv, ... and a JSON
manifest <out-prefix>_manifest.json describing the project->page->column->global-number
mapping. A period with <=max projects still gets a one-page manifest.
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict

_PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pipeline")
sys.path.insert(0, os.path.abspath(_PIPELINE_DIR))  # repo settings, under `python -I` too
try:
    from settings import get as _setting  # noqa: E402
    DEFAULT_MAX_PER_PAGE = int(_setting("max_projects_per_page"))
except ImportError:  # running outside the repo layout
    DEFAULT_MAX_PER_PAGE = 10


def load_rows(csv_path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames


def order_projects(rows, order):
    totals = defaultdict(float)
    first_seen = {}
    for i, r in enumerate(rows):
        p = r["PROJECT"]
        totals[p] += float(r["HOURS"])
        if p not in first_seen:
            first_seen[p] = i

    if order == "largest_hours_first":
        return sorted(totals.keys(), key=lambda p: -totals[p])
    elif order == "alphabetical":
        return sorted(totals.keys())
    elif order == "chronological":
        return sorted(totals.keys(), key=lambda p: first_seen[p])
    else:
        raise ValueError(f"Unknown order: {order}")


def split(rows, fieldnames, max_per_page, order, out_prefix):
    project_order = order_projects(rows, order)
    total_projects = len(project_order)

    pages = []
    for start in range(0, total_projects, max_per_page):
        pages.append(project_order[start:start + max_per_page])

    manifest = {"pages": [], "total_projects": total_projects, "page_count": len(pages)}
    global_number = 1
    page_paths = []

    for page_idx, page_projects in enumerate(pages, start=1):
        # Stable sort by the page's project order, so each project's rows stay in their
        # original relative order but the first-appearance column order matches the manifest.
        page_rank = {p: i for i, p in enumerate(page_projects)}
        page_rows = sorted((r for r in rows if r["PROJECT"] in page_rank), key=lambda r: page_rank[r["PROJECT"]])
        out_path = f"{out_prefix}_{page_idx}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            for r in page_rows:
                writer.writerow([r[fn] for fn in fieldnames])
        page_paths.append(out_path)

        column_map = {}  # local column (1-based, in this page's own grid) -> global project number
        for local_col, proj_name in enumerate(page_projects, start=1):
            column_map[local_col] = global_number
            global_number += 1

        manifest["pages"].append({
            "page_number": page_idx,
            "csv_path": out_path,
            "project_names_in_order": page_projects,
            "local_column_to_global_number": column_map,
            "row_count": len(page_rows),
        })

    return manifest, page_paths


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input_csv")
    parser.add_argument("--max-per-page", type=int, default=DEFAULT_MAX_PER_PAGE)
    parser.add_argument("--order", choices=["largest_hours_first", "alphabetical", "chronological"], default="largest_hours_first")
    parser.add_argument("--out-prefix", default="page")
    args = parser.parse_args()
    if not 1 <= args.max_per_page <= 10:
        parser.error("--max-per-page must be 1-10 (the form has 10 project columns)")

    rows, fieldnames = load_rows(args.input_csv)
    if not rows:
        sys.exit("{} has no data rows -- nothing to split.".format(args.input_csv))
    manifest, page_paths = split(rows, fieldnames, args.max_per_page, args.order, args.out_prefix)

    manifest_path = f"{args.out_prefix}_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Split into {manifest['page_count']} page(s):", file=sys.stderr)
    for p in manifest["pages"]:
        print(f"  Page {p['page_number']}: {p['csv_path']} -- {len(p['project_names_in_order'])} projects, "
              f"{p['row_count']} rows, global numbers {min(p['local_column_to_global_number'].values())}-"
              f"{max(p['local_column_to_global_number'].values())}", file=sys.stderr)
    print(f"Manifest written to {manifest_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
