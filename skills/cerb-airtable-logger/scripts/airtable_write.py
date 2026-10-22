"""
Direct-Airtable-REST-API batch writer for the cerb-airtable-logger skill.

A direct Airtable REST API alternative to an assistant's Airtable connector: one summary line
per batch instead of echoing every field back through the conversation.

Usage:
    python airtable_write.py --input <records.json> [--table "Time Tracking"] [--typecast]
                              [--dry-run] [--chunk-size 10]

<records.json> must be a JSON list of {"fields": {...}} objects, e.g.:
    [
      {"fields": {"Date": "2027-02-12", "Project (linked)": ["recEXAMPLE0000001"], "Hours": 7200,
                   "Description": "2 Hr - Community Library Renovation - worked on drawings",
                   "CERB Section": ["A8: Design Development"]}},
      ...
    ]
"Project (linked)" takes the Project Metadata record ID resolved in cerb-airtable-logger SKILL.md
step 4. Table and field names: airtable/AIRTABLE-SCHEMA.md. --table accepts the table name
(default "Time Tracking") or its tbl... ID.

Writes sequentially in chunks of <= 10 (the Airtable REST limit). Stops immediately on the first
failed chunk and reports exactly how many records were written before the failure -- no blind
retry, no partial chunk left ambiguous.
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

AIRTABLE_RECORD_LIMIT = 10  # hard REST API limit for create_records
RATE_LIMIT_SLEEP = 0.25     # >5 req/sec/base is enforced by Airtable; stay comfortably under
MAX_RETRIES = 3

DEFAULT_TABLE = "Time Tracking"  # table name per airtable/AIRTABLE-SCHEMA.md (an ID also works)
REQUEST_TIMEOUT = 30  # seconds -- never hang forever on a stalled connection

# This file is skills/cerb-airtable-logger/scripts/ -- the repo root is three levels up.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def resolve_env_file():
    """The .env holding AIRTABLE_TOKEN/AIRTABLE_BASE_ID: $CERB_ENV_FILE if set, else the
    repo's pipeline/.env (same file the pipeline scripts use)."""
    override = os.getenv("CERB_ENV_FILE")
    if override:
        return override
    return os.path.join(REPO_ROOT, "pipeline", ".env")


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def post_batch(url, headers, records, typecast):
    body = {"records": records}
    if typecast:
        body["typecast"] = True

    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.post(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return resp.json()["records"]
        if resp.status_code == 429 and attempt < MAX_RETRIES:
            retry_after = float(resp.headers.get("Retry-After", 1))
            time.sleep(retry_after)
            continue
        raise RuntimeError(f"Airtable API error {resp.status_code}: {resp.text}")

    raise RuntimeError("Exhausted retries on 429 rate-limit response")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Path to a JSON file: list of {fields: {...}} records")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Airtable table name or ID (default: Time Tracking)")
    parser.add_argument("--typecast", action="store_true", help="Scope typecast=true to this entire write call")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report counts without writing")
    parser.add_argument("--chunk-size", type=int, default=AIRTABLE_RECORD_LIMIT)
    args = parser.parse_args()

    if args.chunk_size > AIRTABLE_RECORD_LIMIT:
        sys.exit(f"--chunk-size cannot exceed the Airtable API limit of {AIRTABLE_RECORD_LIMIT}")

    env_path = resolve_env_file()
    load_dotenv(env_path)
    token = os.getenv("AIRTABLE_TOKEN")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not token or not base_id:
        sys.exit(f"Missing AIRTABLE_TOKEN or AIRTABLE_BASE_ID in {env_path}")

    with open(args.input, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list) or not records:
        sys.exit("Input JSON must be a non-empty list of {fields: {...}} records")

    for i, r in enumerate(records):
        if "fields" not in r:
            sys.exit(f"Record {i} is missing a top-level 'fields' key")

    url = f"https://api.airtable.com/v0/{base_id}/{quote(args.table, safe='')}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    batches = list(chunked(records, args.chunk_size))
    print(f"{len(records)} records in {len(batches)} batch(es) of <= {args.chunk_size}, "
          f"table {args.table}, typecast={args.typecast}, dry_run={args.dry_run}")

    if args.dry_run:
        print("Dry run only -- nothing written.")
        return

    written = 0
    created_ids = []
    for batch_num, batch in enumerate(batches, start=1):
        try:
            created = post_batch(url, headers, batch, args.typecast)
        except (RuntimeError, requests.RequestException) as e:
            # RequestException covers timeouts/connection drops -- same clean stop, so the
            # written-before-failure count is still reported. A timed-out batch MAY have been
            # written server-side; check Airtable before re-running it.
            print(f"FAILED on batch {batch_num}/{len(batches)} -- {written} records written before failure.")
            print(str(e))
            sys.exit(1)
        written += len(created)
        created_ids.extend(rec["id"] for rec in created)
        print(f"Batch {batch_num}/{len(batches)} OK -- {written}/{len(records)} written")
        if batch_num < len(batches):
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"Done -- {written} records written. First ID: {created_ids[0]}  Last ID: {created_ids[-1]}")


if __name__ == "__main__":
    main()
