#!/usr/bin/env python3
"""
run_period.py -- one entry point for building a CERB submission period.

Two steps, with the AI-written narrative in between:

  1) prepare: fetch (or read offline fixtures), filter to the period, convert to
     the CSV the grid builder expects, convert Project Metadata, split into form
     pages, and compute the hours grid(s). Everything lands in
     exports/<end>/work/. Then it tells you to have your AI assistant write
     exports/<end>/content.json.

        python -I pipeline/run_period.py prepare --start 2027-01-01
        python -I pipeline/run_period.py prepare --start 2027-01-01 --end 2027-06-30
        python -I pipeline/run_period.py prepare --start 2027-01-01 \\
            --offline examples/raw_records.json --offline-metadata examples/project_metadata.json

  2) build: fill the official PDF form (one file per sheet), build the
     Project Descriptions docx, write meta.json and refresh the dashboard.

        python -I pipeline/run_period.py build --end 2027-06-30
        python -I pipeline/run_period.py build --end 2027-06-30 --final

Each step reuses the individual scripts (run as subprocesses), so they can still
be run one by one -- see pipeline/README.md. Settings come from
pipeline/settings.json (see settings.example.json).
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # sibling imports under `python -I`
from filter_by_date import (  # noqa: E402
    PERIOD_MONTHS, CERB_HOURS_CAP, apply_hours_cap, filter_records, load_internal_project_ids,
    load_records, period_end, write_filtered,
)
from metadata_from_airtable import convert as convert_metadata  # noqa: E402
from period_paths import export_dir_for, workdir_for  # noqa: E402
from settings import REPO_ROOT, exports_dir, form_pdf_path, load_settings  # noqa: E402

PY = [sys.executable, "-I"]
ADAPTER = REPO_ROOT / "tools" / "airtable-adapter" / "airtable_to_cerb_csv.py"
SPLITTER = REPO_ROOT / "tools" / "airtable-adapter" / "split_multipage.py"
GRID = REPO_ROOT / "skills" / "cerb-submission-builder" / "scripts" / "build_hours_grid.py"
FIELD_VALUES = REPO_ROOT / "skills" / "cerb-submission-builder" / "scripts" / "generate_pdf_field_values.py"
DOCX = REPO_ROOT / "tools" / "docx-builder" / "build.py"
FILL = HERE / "fill_fillable_fields.py"
META = HERE / "generate_meta.py"
DASHBOARD = HERE / "generate_dashboard.py"
VAULT = HERE / "content_to_vault.py"

BASE_IDENTIFICATION = HERE / "identification.json"
BLANK_IDENTIFICATION = HERE / "identification.example.json"
EXAMPLE_IDENTIFICATION = REPO_ROOT / "examples" / "identification.example.json"


def rel(path):
    """Repo-relative display path where possible."""
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def run(cmd, label, allow_fail=False):
    print("\n-- {} --".format(label))
    result = subprocess.run([str(c) for c in cmd], cwd=str(REPO_ROOT))
    if result.returncode != 0 and not allow_fail:
        sys.exit("Step failed: {} (exit {}).".format(label, result.returncode))
    return result.returncode


def valid_date(text):
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD, got {!r}".format(text))


# ---------------------------------------------------------------------------
# prepare
# ---------------------------------------------------------------------------

def _identification_for_period(source, start, end):
    with open(source, encoding="utf-8") as f:
        ident = json.load(f)
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    ident.update({
        "period_from_day": str(s.day), "period_from_month": str(s.month), "period_from_year": str(s.year),
        "period_to_day": str(e.day), "period_to_month": str(e.month), "period_to_year": str(e.year),
    })
    return ident


def _pick_identification(explicit, offline):
    if explicit:
        return Path(explicit), None
    if BASE_IDENTIFICATION.exists():
        return BASE_IDENTIFICATION, None
    if offline and EXAMPLE_IDENTIFICATION.exists():
        return EXAMPLE_IDENTIFICATION, ("pipeline/identification.json not found -- using the fictional "
                                        "examples/identification.example.json for this offline run.")
    return BLANK_IDENTIFICATION, ("pipeline/identification.json not found -- the form's identification "
                                  "fields will be blank. Copy pipeline/identification.example.json to "
                                  "pipeline/identification.json and fill it in.")


def _rewrite_csv(csv_path, drop, merge):
    """Apply --drop-project / --merge to the period CSV (presentation only -- Airtable is untouched)."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames, rows = reader.fieldnames, list(reader)
    names = {r["PROJECT"] for r in rows}
    notes = []
    for name in list(drop) + list(merge):
        if name not in names:
            notes.append("WARNING: project {!r} (from --drop-project/--merge) has no rows this period.".format(name))
    kept, dropped_hours = [], {}
    for r in rows:
        if r["PROJECT"] in drop:
            dropped_hours[r["PROJECT"]] = dropped_hours.get(r["PROJECT"], 0.0) + float(r["HOURS"])
            continue
        if r["PROJECT"] in merge:
            r["PROJECT"] = merge[r["PROJECT"]]
        kept.append(r)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept)
    for name, hrs in sorted(dropped_hours.items()):
        notes.append("Dropped for this period (still in Airtable): {} ({:.2f} hrs)".format(name, hrs))
    for src, dst in sorted(merge.items()):
        if src in names:
            notes.append("Merged for this period (Airtable untouched): {} -> {}".format(src, dst))
    return notes, len(kept)


def cmd_prepare(args):
    settings = load_settings()
    start = args.start

    # 1. Records + project metadata (Airtable, or offline fixtures)
    if args.offline:
        if not args.offline_metadata:
            sys.exit("--offline needs --offline-metadata too (the Project Metadata export).")
        records_path, metadata_path = Path(args.offline), Path(args.offline_metadata)
        print("Offline mode: {} + {}".format(rel(records_path), rel(metadata_path)))
    else:
        run(PY + [HERE / "fetch_records.py"], "Fetch Time Tracking records from Airtable")
        run(PY + [HERE / "fetch_project_metadata.py"], "Fetch Project Metadata from Airtable")
        records_path, metadata_path = HERE / "raw_records.json", HERE / "project_metadata.json"

    records = load_records(records_path)
    with open(metadata_path, encoding="utf-8") as f:
        metadata_records = json.load(f)
    internal_ids = load_internal_project_ids(metadata_path)

    # 2. Period end: explicit, else period_months after start, cut back to the last logged
    #    entry in that window, then to the hours cap.
    capped = False
    if args.end:
        end = args.end
        end_note = "given"
    else:
        boundary = period_end(start)
        in_window = [r.get("fields", {}).get("Date", "") for r in records
                     if start <= r.get("fields", {}).get("Date", "") <= boundary]
        if not in_window:
            sys.exit("No records between {} and {}.".format(start, boundary))
        end = max(in_window)
        end, capped = apply_hours_cap(records, start, end, internal_ids)
        end_note = "last entry within {} months of the start".format(PERIOD_MONTHS)
        if capped:
            end_note = "capped at {:.0f} eligible hours".format(CERB_HOURS_CAP)
    if end < start:
        sys.exit("End date {} is before start date {}.".format(end, start))

    workdir = workdir_for(end)
    export_dir = export_dir_for(end)
    filtered = filter_records(records, start, end)
    filtered_path = write_filtered(filtered, end)
    print("\nPeriod: {} -> {} ({})".format(start, end, end_note))
    print("Records in period: {}  ->  {}".format(len(filtered), rel(filtered_path)))

    # 3. Adapter -> CSV (+ exclusion report)
    csv_path, report_path = workdir / "cerb_input.csv", workdir / "adapter_report.json"
    run(PY + [ADAPTER, filtered_path, metadata_path, csv_path, "--report", report_path],
        "Convert records to CSV")
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    # 4. Optional per-period presentation changes
    merge = {}
    for item in args.merge or []:
        if "=" not in item:
            sys.exit("--merge expects \"Source Name=Target Name\", got {!r}".format(item))
        src, dst = (part.strip() for part in item.split("=", 1))
        merge[src] = dst
    csv_notes, row_count = _rewrite_csv(csv_path, set(args.drop_project or []), merge)
    if row_count == 0:
        sys.exit("No CERB-eligible rows in this period -- check CERB Section / Non-Project flags.")

    # 5. Project Metadata -> metadata.json
    metadata, meta_warnings = convert_metadata(metadata_records)
    with open(workdir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 6. identification.json for this period
    id_source, id_note = _pick_identification(args.identification, bool(args.offline))
    with open(workdir / "identification.json", "w", encoding="utf-8") as f:
        json.dump(_identification_for_period(id_source, start, end), f, indent=2, ensure_ascii=False)

    # 7. Split into form pages, then one hours grid per page
    for old in list(workdir.glob("page_*.csv")) + list(workdir.glob("grid_*.json")) + \
            list(workdir.glob("field_values_*.json")):
        old.unlink()  # stale pages from an earlier prepare of this period
    per_page = settings["max_projects_per_page"]
    run(PY + [SPLITTER, csv_path, "--max-per-page", per_page, "--order", "largest_hours_first",
              "--out-prefix", workdir / "page"], "Split into form pages")
    with open(workdir / "page_manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)
    grand_total = 0.0
    grid_warnings = []
    for page in manifest["pages"]:
        n = page["page_number"]
        grid_path = workdir / "grid_{}.json".format(n)
        run(PY + [GRID, workdir / "page_{}.csv".format(n), "--out", grid_path], "Hours grid, page {}".format(n))
        with open(grid_path, encoding="utf-8") as f:
            grid = json.load(f)
        grand_total += grid["grand_total"]
        grid_warnings += grid.get("warnings", [])

    # 8. Summary + next step
    print("\n" + "=" * 72)
    print("PREPARED  {} -> {}".format(start, end))
    print("=" * 72)
    project_hours = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            project_hours[r["PROJECT"]] = project_hours.get(r["PROJECT"], 0.0) + float(r["HOURS"])
    number = 0
    for page in manifest["pages"]:
        print("Sheet {}:".format(page["page_number"]))
        for name in page["project_names_in_order"]:
            number += 1
            missing = "" if metadata.get(name) else "   [no Project Metadata details]"
            print("  ({:>2}) {:<45} {:>8.2f} hrs{}".format(number, name, project_hours[name], missing))
    print("Eligible hours on the form: {:.2f}".format(grand_total))
    print("Excluded: {} rows / {} hrs flagged Non-Project / Internal; {} rows / {} hrs internal buckets "
          "without a section; {} rows / {} hrs REAL projects without a CERB Section (categorize these?)".format(
              report["excluded_flagged_non_project_count"], report["excluded_flagged_non_project_hours"],
              report["excluded_no_section_nonwork_count"], report["excluded_no_section_nonwork_hours"],
              report["excluded_no_section_realproject_count"], report["excluded_no_section_realproject_hours"]))
    if manifest["page_count"] > 1:
        thin = [n for n, h in project_hours.items() if h < settings["thin_project_hours"]]
        if thin:
            print("More than {} projects: continuation sheet(s) numbered {}+. Projects under {} hrs you could "
                  "leave out with --drop-project: {}".format(per_page, per_page + 1, settings["thin_project_hours"],
                                                             ", ".join(sorted(thin))))
    for note in ([id_note] if id_note else []) + csv_notes + meta_warnings + \
            ["Adapter: " + w for w in report.get("warnings", [])] + ["Grid: " + w for w in grid_warnings]:
        print("NOTE: " + note)

    content_path = export_dir / "content.json"
    print("\nWorking files: {}/".format(rel(workdir)))
    if content_path.exists():
        print("content.json already exists at {} -- update it if the hours changed.".format(rel(content_path)))
    print("\nNEXT: ask your AI assistant to write {} following the narrative-writing step in AGENTS.md "
          "(inputs: {}/cerb_input.csv and grid_*.json; project numbers as listed above).".format(
              rel(content_path), rel(workdir)))
    print("THEN: python -I pipeline/run_period.py build --end {}".format(end))


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def cmd_build(args):
    end = args.end
    period_dir = exports_dir() / end
    workdir = period_dir / "work"
    manifest_path = workdir / "page_manifest.json"
    if not manifest_path.exists():
        sys.exit("No prepared period at {} -- run `run_period.py prepare` first.".format(rel(workdir)))
    content_path = Path(args.content) if args.content else period_dir / "content.json"
    if not content_path.exists():
        sys.exit("No narrative yet: {} is missing. Ask your AI assistant to write it (see the prepare "
                 "output / AGENTS.md), then re-run build.".format(rel(content_path)))
    out_dir = Path(args.out_dir) if args.out_dir else period_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    ident_path = workdir / "identification.json"
    problems = []

    # 1. Field values per sheet
    for page in manifest["pages"]:
        n = page["page_number"]
        run(PY + [FIELD_VALUES, workdir / "grid_{}.json".format(n), workdir / "metadata.json", ident_path,
                  "--out", workdir / "field_values_{}.json".format(n), "--content", content_path,
                  "--manifest", manifest_path, "--page", n], "PDF field values, sheet {}".format(n))

    # 2. Fill the PDF form(s)
    form = form_pdf_path(args.form)
    if not form.exists():
        problems.append("PDF not filled: the CERB form is not at {}. Download the official fillable form and "
                        "save it there -- see form/README.md (or pass --form PATH).".format(rel(form)))
        print("\n-- Fill PDF form --\n" + problems[-1])
    else:
        for page in manifest["pages"]:
            n = page["page_number"]
            suffix = "_page{}".format(n) if n > 1 else ""
            out_pdf = out_dir / "CERB_Page1_DRAFT_{}{}.pdf".format(end, suffix)
            code = run(PY + [FILL, form, workdir / "field_values_{}.json".format(n), "--out", out_pdf],
                       "Fill PDF form, sheet {}".format(n), allow_fail=True)
            if code != 0:
                problems.append("PDF fill failed for sheet {} (see message above).".format(n))

    # 3. Narrative docx (with the grid consistency check)
    grids = [workdir / "grid_{}.json".format(p["page_number"]) for p in manifest["pages"]]
    run(PY + [DOCX, "--content", content_path, "--identification", ident_path, "--out-dir", out_dir,
              "--grid"] + grids, "Build Project Descriptions docx")

    # 4. meta.json + dashboard (+ optional notes export)
    meta_cmd = PY + [META, "--end-date", end, "--workdir", workdir]
    if args.final:
        meta_cmd.append("--final")
    run(meta_cmd, "Write meta.json")
    run(PY + [DASHBOARD], "Refresh dashboard")
    run(PY + [VAULT, "--content", content_path, "--identification", ident_path], "Optional notes export",
        allow_fail=True)

    print("\n" + "=" * 72)
    print("BUILT  period ending {}  ->  {}/".format(end, rel(out_dir)))
    if problems:
        for p in problems:
            print("PROBLEM: " + p)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare", help="Fetch/filter/convert/split and build the hours grid(s) for a period")
    p.add_argument("--start", required=True, type=valid_date, help="First day of the period (YYYY-MM-DD)")
    p.add_argument("--end", type=valid_date, default=None,
                   help="Last day of the period (default: last logged entry within period_months, "
                        "cut back at period_hours_cap)")
    p.add_argument("--offline", metavar="RAW.json", default=None,
                   help="Use this Time Tracking export instead of calling Airtable")
    p.add_argument("--offline-metadata", metavar="PM.json", default=None,
                   help="Project Metadata export to use with --offline")
    p.add_argument("--identification", default=None,
                   help="Base identification.json (default: pipeline/identification.json)")
    p.add_argument("--drop-project", action="append", metavar="NAME",
                   help="Leave this project out of this period only (repeatable; Airtable untouched)")
    p.add_argument("--merge", action="append", metavar="SOURCE=TARGET",
                   help="Report SOURCE's rows under TARGET for this period only (repeatable; Airtable untouched)")
    p.set_defaults(func=cmd_prepare)

    b = sub.add_parser("build", help="Fill the PDF, build the docx, write meta.json, refresh the dashboard")
    b.add_argument("--end", required=True, type=valid_date, help="Period end date used by prepare")
    b.add_argument("--final", action="store_true", help="Mark this period FINAL in meta.json")
    b.add_argument("--form", default=None, help="Fillable CERB PDF (default: settings form_pdf or $CERB_FORM_PDF)")
    b.add_argument("--content", default=None, help="Narrative JSON (default: exports/<end>/content.json)")
    b.add_argument("--out-dir", default=None, help="Write the PDF(s) and docx here instead of exports/<end>/")
    b.set_defaults(func=cmd_build)

    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)  # keep our output in order with subprocess output
    except AttributeError:
        pass
    args.func(args)


if __name__ == "__main__":
    main()
