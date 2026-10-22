#!/usr/bin/env python3
"""
content_to_vault.py  (optional)

Reads a period's content.json (the CERB project-description narrative) and
writes it as one Markdown note into a notes folder (e.g. an Obsidian vault),
one note per submission period, named by period end date. Flags render as
callouts. content.json stays the source of truth -- edit it, then re-run this
script to refresh the note.

The notes folder comes from $CERB_VAULT_DIR or the CERB_VAULT_DIR key in
pipeline/.env; if it's unset or the folder doesn't exist, nothing is written.
Notes go into --subdir (default "CERB") inside that folder. --tags adds a
"Tags:" line (e.g. --tags "#CERB #IAP"); omitted means no tag line.
The note's date comes from identification.json's period_to fields, or
--end-date -- never today's date, which would silently misfile the note.

    python content_to_vault.py --content ../exports/2027-06-30/content.json --end-date 2027-06-30
    python content_to_vault.py --content ../exports/2027-06-30/content.json \\
        --identification ../exports/2027-06-30/work/identification.json --tags "#CERB"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from period_paths import vault_dir  # noqa: E402

HERE = Path(__file__).parent
IDENTIFICATION_JSON = HERE / "identification.json"


def load_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def period_end_date(ident):
    y = ident.get("period_to_year", "")
    m = ident.get("period_to_month", "")
    d = ident.get("period_to_day", "")
    if y and m and d:
        return "{}-{:0>2}-{:0>2}".format(y, m, d)
    return None


def build_note(content, tags=None):
    title = content.get("title", "Project Descriptions")
    subtitle = content.get("subtitle", "")
    note_text = content.get("note", "")
    projects = content.get("projects", [])
    exclusions = content.get("exclusions", [])
    flags_summary = content.get("flags_summary", "")

    lines = []
    if tags:
        lines.append("Tags: {}".format(tags))
        lines.append("")
    lines.append("# {}".format(title))
    lines.append("")
    if subtitle:
        lines.append("*{}*".format(subtitle))
        lines.append("")
    if note_text:
        lines.append("> [!warning] {}".format(note_text))
        lines.append("")

    for project in projects:
        lines.append("## {}. {}".format(project.get("number", ""), project.get("name", "")))
        lines.append("")
        meta_bits = []
        for key, label in (("project_type", "Type"), ("occupancy", "Occupancy")):
            val = project.get(key, "")
            if val:
                meta_bits.append("{}: {}".format(label, val))
        if meta_bits:
            lines.append("*{}*".format(" · ".join(meta_bits)))
            lines.append("")

        if project.get("project_brief"):
            lines.append("**Project Brief:**")
            lines.append("")
            lines.append(project["project_brief"])
            lines.append("")
            lines.append("**Architectural Experience Description:**")
            lines.append("")

        for cat in project.get("categories", []):
            lines.append("### {}. {} ({} hrs)".format(
                cat.get("number", ""), cat.get("name", ""), cat.get("hours", 0)))
            lines.append("")
            for bullet in cat.get("bullets", []):
                # A bullet is either a plain string, or {"text": ..., "sub_items": [...]}
                # for the "...including but not limited to:" nested-list convention.
                if isinstance(bullet, dict):
                    lines.append("- {}".format(bullet["text"]))
                    for sub_item in bullet.get("sub_items") or []:
                        lines.append("    - {}".format(sub_item))
                else:
                    lines.append("- {}".format(bullet))
            lines.append("")
            for flag in cat.get("flags") or []:
                lines.append("> [!warning] Flagged for review")
                lines.append("> {}".format(flag))
                lines.append("")

    if exclusions:
        lines.append("## Excluded entries")
        lines.append("")
        for exclusion in exclusions:
            lines.append("- {}".format(exclusion))
        lines.append("")

    if flags_summary:
        lines.append("---")
        lines.append("*{}*".format(flags_summary))
        lines.append("")

    lines.append("---")
    lines.append("*Exported from `content.json` by `content_to_vault.py` "
                 "— edit the source JSON, not this note; re-run the script to refresh.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--content", required=True, help="Path to this period's content.json")
    parser.add_argument(
        "--identification", default=None,
        help="Path to this period's identification.json (default: next to --content, then its work/ "
             "subfolder, then pipeline/identification.json)",
    )
    parser.add_argument("--end-date", default=None,
                        help="Period end date (YYYY-MM-DD) naming the note; overrides identification.json")
    parser.add_argument("--subdir", default="CERB", help="Subfolder inside the notes folder (default: CERB)")
    parser.add_argument("--tags", default=None, help='Optional tag line, e.g. "#CERB #IAP"')
    args = parser.parse_args()

    notes_root = vault_dir()
    if notes_root is None:
        print("CERB_VAULT_DIR not set (optional) -- skipping the Markdown export.")
        return
    if not notes_root.exists():
        print("Notes folder not found at {} -- skipping the Markdown export.".format(notes_root))
        return

    content_path = Path(args.content)
    content = load_json(content_path)
    if not content:
        print("No content.json found at {} -- nothing to export.".format(content_path))
        return

    end_date = args.end_date
    if not end_date:
        candidates = ([Path(args.identification)] if args.identification else [
            content_path.parent / "identification.json",
            content_path.parent / "work" / "identification.json",
            IDENTIFICATION_JSON,
        ])
        id_path = next((p for p in candidates if p.exists()), candidates[-1])
        end_date = period_end_date(load_json(id_path))
        if not end_date:
            sys.exit("No period_to_year/month/day in {} -- pass --end-date YYYY-MM-DD to name the note.".format(id_path))

    out_dir = notes_root / args.subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "CERB Project Descriptions - {}.md".format(end_date)
    out_path.write_text(build_note(content, args.tags), encoding="utf-8")

    print("Note written: {}".format(out_path))


if __name__ == "__main__":
    main()
