#!/usr/bin/env python3
"""
period_paths.py

Shared helper for locating a submission period's folders.

Every period-scoped intermediate (filtered Airtable records, the converted CSV,
page splits, hours grids, PDF field values, and that period's own
identification.json/metadata.json) lives under exports/{end_date}/work/ -- never
as an unnamespaced file at the pipeline root. Root-level singletons don't
survive building two periods back to back: a later period's run could silently
overwrite an earlier period's exports or have its hours summed into the wrong
meta.json.

    from period_paths import workdir_for, export_dir_for, resolve_identification

    wd = workdir_for("2027-06-30")      # -> exports/2027-06-30/work/, created if needed
    ed = export_dir_for("2027-06-30")   # -> exports/2027-06-30/
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # sibling imports under `python -I`
from settings import exports_dir  # noqa: E402

VAULT_ENV_KEY = "CERB_VAULT_DIR"


def export_dir_for(end_date: str) -> Path:
    d = exports_dir() / end_date
    d.mkdir(parents=True, exist_ok=True)
    return d


def workdir_for(end_date: str) -> Path:
    d = export_dir_for(end_date) / "work"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_identification(primary_path, script_root=HERE) -> Path:
    """
    Resolve the identification.json for a period: prefer the file sitting next to
    `primary_path` (a field_values.json, content.json, etc. in that period's work
    folder); fall back to pipeline/identification.json only if no sibling exists,
    and warn loudly when that happens -- the pipeline-level file has no period
    dates of its own, so trusting it silently is how outputs get misdated.
    """
    sibling = Path(primary_path).parent / "identification.json"
    if sibling.exists():
        return sibling

    root_fallback = Path(script_root) / "identification.json"
    print(
        "WARNING: no identification.json next to {} -- falling back to {}. "
        "Its period dates may not match this period.".format(primary_path, root_fallback),
        file=sys.stderr,
    )
    return root_fallback


def env_file() -> Path:
    """The pipeline's .env: $CERB_ENV_FILE if set, else pipeline/.env."""
    override = os.getenv("CERB_ENV_FILE")
    if override:
        return Path(override)
    return HERE / ".env"


def _read_env_value(path, key):
    """Minimal KEY=VALUE lookup so vault-writing scripts don't need python-dotenv."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip().removeprefix("export ").strip() == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return None


def vault_dir():
    """Optional Markdown-notes folder (e.g. an Obsidian vault) from $CERB_VAULT_DIR, else
    the CERB_VAULT_DIR key in the pipeline .env. Returns None when unset -- callers then
    skip their notes step."""
    value = os.getenv(VAULT_ENV_KEY) or _read_env_value(env_file(), VAULT_ENV_KEY)
    return Path(value) if value else None
