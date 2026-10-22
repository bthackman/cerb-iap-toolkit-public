import os
import sys
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from period_paths import env_file  # noqa: E402

load_dotenv(env_file())

token = os.getenv("AIRTABLE_TOKEN")
base_id = os.getenv("AIRTABLE_BASE_ID")

if not token or not base_id:
    sys.exit("Missing AIRTABLE_TOKEN or AIRTABLE_BASE_ID in {} (copy pipeline/.env.example)".format(env_file()))

url = f"https://api.airtable.com/v0/{base_id}/Project%20Metadata"
headers = {"Authorization": f"Bearer {token}"}

all_records = []
params = {}

while True:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        sys.exit(f"API error {response.status_code}: {response.text}")

    data = response.json()
    all_records.extend(data.get("records", []))
    print(f"  Fetched {len(all_records)} records so far...")

    offset = data.get("offset")
    if not offset:
        break
    params["offset"] = offset

output_path = os.path.join(os.path.dirname(__file__), "project_metadata.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_records, f, indent=2, ensure_ascii=False)

print(f"\nTotal records: {len(all_records)}")
print(f"Saved to: {output_path}")
