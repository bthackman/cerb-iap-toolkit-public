#!/usr/bin/env python3
"""
generate_meta.py

Captures the current export state into exports/{end_date}/meta.json.
Run after each CERB export to record hours, period, and draft/final status.

    python generate_meta.py --end-date 2027-06-30            # reads exports/2027-06-30/work/
    python generate_meta.py --end-date 2027-06-30 --final    # mark this submission as FINAL
    python generate_meta.py --end-date 2027-06-30 --draft    # demote a FINAL period back to draft

Without --final/--draft an existing meta.json's "final" status is preserved;
otherwise status is detected from the export filenames.
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # sibling imports under `python -I`
from settings import exports_dir  # noqa: E402


def load_identification(workdir=None):
    id_path = (workdir / "identification.json") if workdir else (HERE / "identification.json")
    if not id_path.exists():
        raise FileNotFoundError("identification.json not found at {}".format(id_path))
    with open(id_path, encoding="utf-8") as f:
        return json.load(f)


def derive_end_date(ident):
    y = ident.get("period_to_year", "")
    m = ident.get("period_to_month", "")
    d = ident.get("period_to_day", "")
    if not (y and m and d):
        raise ValueError("period_to_year/month/day missing in identification.json")
    return "{}-{}-{}".format(y, m.zfill(2), d.zfill(2))


def derive_from_date(ident):
    y = ident.get("period_from_year", "")
    m = ident.get("period_from_month", "")
    d = ident.get("period_from_day", "")
    if not (y and m and d):
        return ""
    return "{}-{}-{}".format(y, m.zfill(2), d.zfill(2))


def sum_grids(workdir=None):
    """Sum grand_total, and per-category hours, across all grid_*.json files for this period.

    Scoped to `workdir` when given; falls back to the pipeline folder, which is
    only correct when exactly one period's grid files are sitting there --
    globbing the root unconditionally used to sum whatever periods' grid
    files happened to be present, silently double-counting hours once a
    second period's files landed alongside the first.

    category_hours is keyed by category number as a string (JSON object keys
    must be strings) so generate_dashboard.py can aggregate it across periods
    and compare cumulative per-category totals against the track's targets.
    """
    search_dir = workdir if workdir else HERE
    total_hours = 0.0
    project_names = set()
    category_hours = {}
    for grid_file in sorted(search_dir.glob("grid_*.json")):
        with open(grid_file, encoding="utf-8") as f:
            g = json.load(f)
        total_hours += g.get("grand_total", 0)
        for proj in g.get("projects", []):
            name = proj["name"] if isinstance(proj, dict) else proj
            project_names.add(name)
        for row in g.get("category_rows", []):
            key = str(row["category_number"])
            category_hours[key] = category_hours.get(key, 0.0) + row.get("row_total", 0.0)
    category_hours = {k: round(v, 2) for k, v in category_hours.items()}
    return total_hours, len(project_names), category_hours


def detect_status(export_dir: Path) -> str:
    """DRAFT if any output file has _DRAFT in its name, or if there are no PDF/docx
    outputs in the folder at all; FINAL only when outputs exist and none is a draft."""
    outputs = [f for f in export_dir.iterdir()
               if f.is_file() and f.suffix.lower() in (".pdf", ".docx")]
    if not outputs or any("_DRAFT" in f.name.upper() for f in outputs):
        return "draft"
    return "final"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    status_group = parser.add_mutually_exclusive_group()
    status_group.add_argument("--final", action="store_true", help="Mark this submission as FINAL instead of draft")
    status_group.add_argument("--draft", action="store_true", help="Explicitly mark this submission as draft (demotes a FINAL period)")
    parser.add_argument("--end-date", default=None, help="Override end date (YYYY-MM-DD); default: read from identification.json")
    parser.add_argument(
        "--workdir", default=None,
        help="Per-period working directory holding this period's identification.json and grid_*.json "
             "(default: exports/{end_date}/work/ when --end-date is given).",
    )
    args = parser.parse_args()

    workdir = Path(args.workdir) if args.workdir else None
    if workdir is None and args.end_date:
        candidate = exports_dir() / args.end_date / "work"
        if candidate.exists():
            workdir = candidate
    if workdir is None:
        print(
            "WARNING: no --workdir/--end-date given -- reading identification.json and grid_*.json from "
            "the pipeline folder. Only correct if exactly one period's files are there right now.",
            file=sys.stderr,
        )

    ident = load_identification(workdir)

    end_date = args.end_date or derive_end_date(ident)
    from_date = derive_from_date(ident)

    export_dir = exports_dir() / end_date
    if not export_dir.exists():
        print("Export folder not found: {}".format(export_dir))
        print("Run the PDF fill and docx build scripts first.")
        return

    total_hours, project_count, category_hours = sum_grids(workdir)

    meta_path = export_dir / "meta.json"
    previous_status = None
    if meta_path.exists():
        try:
            with open(meta_path, encoding="utf-8") as f:
                previous_status = json.load(f).get("status")
        except (OSError, ValueError):
            previous_status = None

    # The pipeline always writes _DRAFT_ filenames, so detect_status() alone would
    # demote a period already marked final every time this is re-run. Only an
    # explicit --draft is allowed to do that.
    if args.final:
        status = "final"
    elif args.draft:
        status = "draft"
    elif previous_status == "final":
        status = "final"
    else:
        status = detect_status(export_dir)

    meta = {
        "period_from": from_date,
        "period_to": end_date,
        "total_hours": total_hours,
        "projects": project_count,
        "category_hours": category_hours,
        "status": status,
        "generated": date.today().isoformat(),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print("Written: {}".format(meta_path))
    print("  Period : {} -> {}".format(from_date, end_date))
    print("  Hours  : {:.2f}".format(total_hours))
    print("  Projects: {}".format(project_count))
    print("  Status : {}".format(status.upper()))


if __name__ == "__main__":
    main()
