#!/usr/bin/env python3
"""
plan_backlog_periods.py

Planning helper for catching up on several unsubmitted periods at once: walks
forward from a start date (default: the earliest record) in chunks of
period_months / period_hours_cap (settings), and prints the resulting period
sequence up to a ceiling date. Read-only -- it builds nothing; run
`run_period.py prepare --start ... --end ...` for each printed period, one at a time.

    python plan_backlog_periods.py
    python plan_backlog_periods.py --start 2027-01-01 --until 2028-12-31
    python plan_backlog_periods.py --records ../examples/raw_records.json --project-metadata ../examples/project_metadata.json
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from filter_by_date import (  # noqa: E402
    CERB_HOURS_CAP, PROJECT_METADATA, RAW_RECORDS, apply_hours_cap, earliest_record_date,
    is_cap_eligible, load_internal_project_ids, load_records, period_end,
)


def compute_period(records, start_date, ceiling_date, internal_project_ids=None):
    end_date = min(period_end(start_date), ceiling_date)
    end_date, capped_by_hours = apply_hours_cap(records, start_date, end_date, internal_project_ids)

    total_hours = sum(
        (r.get("fields", {}).get("Hours", 0) or 0) for r in records
        if start_date <= r.get("fields", {}).get("Date", "") <= end_date
        and is_cap_eligible(r, internal_project_ids)
    ) / 3600.0

    return end_date, total_hours, capped_by_hours


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", default=None, help="First period's start date (default: earliest record date)")
    parser.add_argument("--until", default=None,
                        help="Last date to plan through, inclusive (default: today). Use the day before an "
                             "already-built period to plan only the gap before it.")
    parser.add_argument("--records", default=str(RAW_RECORDS))
    parser.add_argument("--project-metadata", default=str(PROJECT_METADATA))
    args = parser.parse_args()

    records = load_records(args.records)
    internal_project_ids = load_internal_project_ids(args.project_metadata)
    start = args.start or earliest_record_date(records)
    if not start:
        sys.exit("No dated records found.")
    ceiling = args.until or date.today().isoformat()

    periods = []
    current_start = start
    while current_start <= ceiling:
        end_date, hours, capped = compute_period(records, current_start, ceiling, internal_project_ids)
        periods.append((current_start, end_date, hours, capped))
        if end_date >= ceiling:
            break
        current_start = (date.fromisoformat(end_date) + timedelta(days=1)).isoformat()

    print("Planned periods, {} -> {}:\n".format(start, ceiling))
    running_total = 0.0
    for i, (s, e, hrs, capped) in enumerate(periods, 1):
        running_total += hrs
        cap_note = "  [capped at {:.0f} hrs]".format(CERB_HOURS_CAP) if capped else ""
        print("  Period {}: {} -> {}   {:.2f} eligible hrs{}".format(i, s, e, hrs, cap_note))
    print("\nTotal periods: {}".format(len(periods)))
    print("Total eligible hours: {:.2f}".format(running_total))
    if internal_project_ids is None:
        print("(No project metadata file -- Non-Project / Internal rows were counted as eligible.)")


if __name__ == "__main__":
    main()
