#!/usr/bin/env python3
"""
filter_by_date.py

Computes the CERB submission date range and filters raw_records.json to it.

Default range:
  - start_date = day after the most recent FINAL submission's period_to
    (read from exports/*/meta.json). If no FINAL submission exists yet,
    falls back to the earliest date found in the records (prints a note --
    this only happens before your first submission is finalized).
  - end_date = the day before start_date + period_months (settings; default 6,
    end is inclusive, so 2027-01-01 -> 2027-06-30, not 2027-07-01), capped at today.
  - Further capped to whichever comes first between that boundary and
    period_hours_cap (settings; default 1000) cumulative CERB-eligible hours.
    Only rows with a CERB Section count toward the cap (no-section rows never
    reach the form). Rows linked to a "Non-Project / Internal" project are also
    left out of the cap, but only when project_metadata.json (from
    fetch_project_metadata.py) is available to say which projects those are;
    without it they still count.

Override the computed default with --start / --end (YYYY-MM-DD). Providing
both skips the default-computation entirely. --records / --project-metadata
read other files than pipeline/raw_records.json / pipeline/project_metadata.json
(e.g. the offline fixtures in examples/).

Output: exports/{end_date}/work/raw_records_filtered.json

    python filter_by_date.py                      # compute + use default
    python filter_by_date.py --start 2027-01-01 --end 2027-06-30
"""

import argparse
import calendar
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from period_paths import workdir_for  # noqa: E402
from settings import exports_dir, get as setting  # noqa: E402

HERE = Path(__file__).parent
RAW_RECORDS = HERE / "raw_records.json"
PROJECT_METADATA = HERE / "project_metadata.json"
CERB_HOURS_CAP = float(setting("period_hours_cap"))
PERIOD_MONTHS = int(setting("period_months"))


def records_list(data):
    """Airtable exports arrive either as a bare list of records or in the REST
    response shape {"records": [...]}; accept both."""
    if isinstance(data, dict):
        return data.get("records", [])
    return data


def load_records(path=RAW_RECORDS):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("{} not found -- run fetch_records.py first".format(path))
    with open(path, encoding="utf-8") as f:
        return records_list(json.load(f))


def find_last_final_period_to():
    """Scan exports/*/meta.json for the most recent FINAL submission's period_to."""
    best = None
    for meta_path in sorted(exports_dir().glob("*/meta.json")):
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("status") == "final":
            period_to = meta.get("period_to", "")
            if period_to and (best is None or period_to > best):
                best = period_to
    return best


def earliest_record_date(records):
    dates = [r.get("fields", {}).get("Date", "") for r in records]
    dates = [d for d in dates if d]
    return min(dates) if dates else None


def add_months(iso_date, months):
    y, m, d = (int(x) for x in iso_date.split("-"))
    total_months = (y * 12 + (m - 1)) + months
    ny, nm = divmod(total_months, 12)
    nm += 1
    last_day = calendar.monthrange(ny, nm)[1]
    nd = min(d, last_day)
    return "{:04d}-{:02d}-{:02d}".format(ny, nm, nd)


def period_end(start_date, months=None):
    """Inclusive end of a period starting on start_date: the day before
    start_date + months (default: settings period_months)."""
    boundary = date.fromisoformat(add_months(start_date, months or PERIOD_MONTHS))
    return (boundary - timedelta(days=1)).isoformat()


six_month_end = period_end  # backward-compatible name


def load_internal_project_ids(path=PROJECT_METADATA):
    """IDs of Project Metadata records flagged "Non-Project / Internal", or None if
    the project metadata file isn't available (the cap then can't apply that exclusion)."""
    path = Path(path)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        metadata = records_list(json.load(f))
    return {pr["id"] for pr in metadata if pr.get("fields", {}).get("Non-Project / Internal")}


def is_cap_eligible(record, internal_project_ids=None):
    """Whether a record's hours count toward the hours cap: it must have a CERB
    Section, and (when project metadata is known) not link to an internal project --
    the same rows airtable_to_cerb_csv.py drops before the form is built."""
    fields = record.get("fields", {})
    if not fields.get("CERB Section"):
        return False
    links = fields.get("Project (linked)") or []
    if internal_project_ids and links and links[0] in internal_project_ids:
        return False
    return True


def apply_hours_cap(records, start_date, end_date, internal_project_ids=None):
    """Truncate end_date to the date cumulative eligible hours in [start_date, end_date]
    reach CERB_HOURS_CAP. Returns (end_date, capped_by_hours). Shared with
    plan_backlog_periods.py and run_period.py."""
    in_range = sorted(
        (r for r in records
         if start_date <= r.get("fields", {}).get("Date", "") <= end_date
         and is_cap_eligible(r, internal_project_ids)),
        key=lambda r: r.get("fields", {}).get("Date", ""),
    )
    cumulative = 0.0
    hours_cap_hit_date = None
    for r in in_range:
        seconds = r.get("fields", {}).get("Hours", 0) or 0
        cumulative += seconds / 3600.0
        if cumulative >= CERB_HOURS_CAP and hours_cap_hit_date is None:
            hours_cap_hit_date = r.get("fields", {}).get("Date", "")

    capped_by_hours = hours_cap_hit_date is not None and hours_cap_hit_date < end_date
    if capped_by_hours:
        end_date = hours_cap_hit_date
    return end_date, capped_by_hours


def compute_default_range(records, internal_project_ids=None):
    last_final = find_last_final_period_to()
    if last_final:
        y, m, d = (int(x) for x in last_final.split("-"))
        start_date = (date(y, m, d) + timedelta(days=1)).isoformat()
        anchor_note = "day after last FINAL submission ({})".format(last_final)
    else:
        start_date = earliest_record_date(records)
        anchor_note = "no FINAL submission on record -- using earliest record date"
        if start_date is None:
            raise ValueError("No records with a Date field found -- cannot compute a default range")

    today_str = date.today().isoformat()
    end_date = min(period_end(start_date), today_str)

    # Apply hours cap: truncate if cumulative eligible hours hit CERB_HOURS_CAP
    # before the date cap.
    end_date, capped_by_hours = apply_hours_cap(records, start_date, end_date, internal_project_ids)

    return start_date, end_date, anchor_note, capped_by_hours


def filter_records(records, start_date, end_date):
    return [r for r in records if start_date <= r.get("fields", {}).get("Date", "") <= end_date]


def write_filtered(filtered, end_date):
    path = workdir_for(end_date) / "raw_records_filtered.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=None, help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--records", default=str(RAW_RECORDS),
                        help="Time Tracking records JSON (default: pipeline/raw_records.json)")
    parser.add_argument("--project-metadata", default=str(PROJECT_METADATA),
                        help="Project Metadata records JSON (default: pipeline/project_metadata.json)")
    args = parser.parse_args()

    records = load_records(args.records)

    if args.start and args.end:
        start_date, end_date = args.start, args.end
        anchor_note = "manual override"
        capped_by_hours = False
    else:
        internal_project_ids = load_internal_project_ids(args.project_metadata)
        if internal_project_ids is None:
            print(
                "NOTE: {} not found -- Non-Project/Internal rows still count toward the "
                "{:.0f}-hr cap (run fetch_project_metadata.py to exclude them).".format(
                    args.project_metadata, CERB_HOURS_CAP),
                file=sys.stderr,
            )
        start_date, end_date, anchor_note, capped_by_hours = compute_default_range(records, internal_project_ids)
        if args.start:
            start_date = args.start
        if args.end:
            end_date = args.end

    filtered = filter_records(records, start_date, end_date)
    total_hours = sum((r.get("fields", {}).get("Hours", 0) or 0) for r in filtered) / 3600.0
    filtered_path = write_filtered(filtered, end_date)

    print("Range anchor: {}".format(anchor_note))
    print("Period: {} -> {}".format(start_date, end_date))
    if capped_by_hours:
        print("  (truncated early -- hit the {:.0f}-hr cap before the {}-month boundary)".format(
            CERB_HOURS_CAP, PERIOD_MONTHS))
    print("Total records in {}: {}".format(Path(args.records).name, len(records)))
    print("Records in range: {} ({:.2f} hrs)".format(len(filtered), total_hours))
    print("Workdir for this period: {}".format(filtered_path.parent))
    print("Written: {}".format(filtered_path))


if __name__ == "__main__":
    main()
