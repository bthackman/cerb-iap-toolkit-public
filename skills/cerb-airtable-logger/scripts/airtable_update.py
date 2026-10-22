"""
Direct-Airtable-REST-API batch updater for the cerb-airtable-logger skill. Sibling to
airtable_write.py -- same token/chunking/retry discipline, but PATCHes existing records
by id instead of creating new ones (e.g. backfilling a CERB Section suggestion onto
records already written without one).

Usage:
    python airtable_update.py --input <updates.json> [--table "Time Tracking"] [--dry-run]

<updates.json> must be a JSON list of {"id": "rec...", "fields": {...}} objects.
--table accepts the table name (default "Time Tracking", see airtable/AIRTABLE-SCHEMA.md)
or its tbl... ID.
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import quote

import requests
from dotenv import load_dotenv

AIRTABLE_RECORD_LIMIT = 10
RATE_LIMIT_SLEEP = 0.25
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


def patch_batch(url, headers, records):
    body = {"records": records}
    for attempt in range(1, MAX_RETRIES + 1):
        resp = requests.patch(url, headers=headers, json=body, timeout=REQUEST_TIMEOUT)
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
    parser.add_argument("--input", required=True, help="Path to a JSON file: list of {id, fields} records")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Airtable table name or ID (default: Time Tracking)")
    parser.add_argument("--dry-run", action="store_true")
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
        sys.exit("Input JSON must be a non-empty list of {id, fields} records")
    for i, r in enumerate(records):
        if "id" not in r or "fields" not in r:
            sys.exit(f"Record {i} is missing 'id' or 'fields'")

    url = f"https://api.airtable.com/v0/{base_id}/{quote(args.table, safe='')}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    batches = list(chunked(records, args.chunk_size))
    print(f"{len(records)} records in {len(batches)} batch(es) of <= {args.chunk_size}, "
          f"table {args.table}, dry_run={args.dry_run}")

    if args.dry_run:
        print("Dry run only -- nothing updated.")
        return

    updated = 0
    for batch_num, batch in enumerate(batches, start=1):
        try:
            result = patch_batch(url, headers, batch)
        except (RuntimeError, requests.RequestException) as e:
            # RequestException covers timeouts/connection drops -- same clean stop, so the
            # updated-before-failure count is still reported.
            print(f"FAILED on batch {batch_num}/{len(batches)} -- {updated} records updated before failure.")
            print(str(e))
            sys.exit(1)
        updated += len(result)
        print(f"Batch {batch_num}/{len(batches)} OK -- {updated}/{len(records)} updated")
        if batch_num < len(batches):
            time.sleep(RATE_LIMIT_SLEEP)

    print(f"Done -- {updated} records updated.")


if __name__ == "__main__":
    main()
