import os
import sys
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

url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(url, headers=headers, timeout=30)

if response.status_code != 200:
    sys.exit(f"API error {response.status_code}: {response.text}")

tables = response.json().get("tables", [])
print(f"Found {len(tables)} table(s) in base {base_id}:\n")

for table in tables:
    print(f"Table: {table['name']}")
    for field in table.get("fields", []):
        print(f"  - {field['name']} ({field['type']})")
    print()
