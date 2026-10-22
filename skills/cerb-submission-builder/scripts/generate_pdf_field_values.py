#!/usr/bin/env python3
"""
generate_pdf_field_values.py

Builds the field_values.json needed by pipeline/fill_fillable_fields.py, using:
  - the hours-grid JSON produced by build_hours_grid.py
  - project metadata (location, type, occupancy, GFA, budget, storeys) -- metadata.json from
    pipeline/metadata_from_airtable.py (cerb-submission-builder SKILL.md step 3)
  - identification info (intern/employer/mentor/period) supplied directly

This script ONLY fills the in-scope fields: identification, the Role of Intern synopsis (with
--content), Summary of Projects, and the Summary of Experience hours grid (plus the optional
backlog fields below). It deliberately does not touch declaration/signature fields.

IMPORTANT: this script explicitly clears every in-scope field it does not otherwise have a value
for, rather than leaving it untouched. This is necessary in practice -- a PDF used as the fill
template may itself be a prior submission with real data already saved in its fields. Without
explicit clearing, any field this run doesn't supply would silently retain whatever was already in
the source PDF, which could leak stale personal/project data into what's meant to be a fresh draft.
Out-of-scope fields (signatures, declarations, association-use-only, and page 5 unless backlog
auto-fill is on) are never touched in either direction -- not filled, not cleared.

USAGE:
    python generate_pdf_field_values.py <grid.json> <metadata.json> <identification.json> --out field_values.json [--content content.json]
        [--manifest page_manifest.json --page N]

metadata.json shape: {"Project Name": {"location": ..., "project_type": ..., "occupancy": ...,
    "gross_floor_area": ..., "budget": ..., "storeys": ...}, ...}
    Any missing field for a project is simply omitted from the output (left blank on the form) --
    this script does not invent placeholder text for missing metadata.

identification.json shape: see EXAMPLE_IDENTIFICATION below for all expected keys.

--content content.json (optional, the docx-builder's source file) enables two features:
  - Role of Intern / "Project(s):" narrative field (page 2) is auto-filled from each project's
    `project_brief` text: the header line from settings role_of_intern_header, then
    "(N) <name>\n<brief>" per project. Without --content this field is left untouched.
  - Each project's Summary of Projects table name (page 3) is taken from content.json's `name`
    (matched by project `number` == the grid's project `column`) instead of the grid's own name,
    so the docx and the numeric PDF form can never drift apart on a project's display name --
    content.json is the authoritative source since that's the file that gets edited by hand. Falls
    back to the grid's name if content.json has no matching project number.

--manifest/--page (multi-page periods, >10 projects): split_multipage.py's manifest maps each page's
local grid column (always restarting at 1) to the global project number (11, 12, 13... on page 2).
With it, content.json lookup, the Role of Intern synopsis (only this page's projects), and the
Summary of Projects names (prefixed "(11) " etc. on page 2+, per the manual's renumbering
instruction) all use the global number. Without it every column is its own global number, which is
exactly the single-page behaviour.

Optional backlog auto-fill (settings backlog_cutoff_date, default null = off): when set to a
YYYY-MM-DD date, periods whose end date falls BEFORE it get settings backlog_text (default
"N/A BACKLOG HOURS") written into Mentor Identification's Surname field, all 4 Comments-by-Employer
boxes, and the Mentor Declaration name field; later periods get those page-5 fields explicitly
cleared. With the setting off, the page-5 fields are never touched. See cerb_pdf_field_map.py's
COMMENTS_FIELDS/MENTOR_DECLARATION_NAME_FIELD for the field names. Use this only if your jurisdiction
accepts retroactive backlog submissions in that form.
"""

import argparse
import json
import os
import sys
from datetime import date

# os.path rather than splitting on "/" -- a backslash Windows path left the script's own folder
# off sys.path, which `python -I` (no implicit script-dir entry) then exposed as an ImportError.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cerb_pdf_field_map as fmap  # noqa: E402

# Repo settings (pipeline/settings.py); fall back to built-in defaults outside the repo layout.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "pipeline")))
try:
    from settings import load_settings  # noqa: E402
    _SETTINGS = load_settings()
except ImportError:
    _SETTINGS = {}

BACKLOG_TEXT = _SETTINGS.get("backlog_text") or "N/A BACKLOG HOURS"
BACKLOG_CUTOFF_DATE = _SETTINGS.get("backlog_cutoff_date")  # None/null = backlog auto-fill off
ROLE_OF_INTERN_HEADER = _SETTINGS.get("role_of_intern_header") or (
    "** Refer to the attached Project Descriptions document for full project details and hours. "
    "Synopsis listed below:"
)

EXAMPLE_IDENTIFICATION = {
    "intern_surname": "", "intern_first_name": "", "intern_middle_names": "",
    "intern_address": "", "intern_suite_no": "", "intern_city": "",
    "intern_province_state_territory": "", "intern_country": "", "intern_postal_zip": "",
    "intern_phone": "",
    "employer_practice_name": "", "employer_address": "", "employer_suite_no": "",
    "employer_city": "", "employer_country": "", "employer_province_state_territory": "",
    "employer_postal_zip": "", "employer_phone": "", "employer_email": "",
    "employer_nature_of_activities": "", "experience_supervisor": "",
    "experience_supervisor_position": "",
    "mentor_surname": "", "mentor_first_name": "", "mentor_res_telephone": "",
    "mentor_practice_name": "", "mentor_bus_telephone": "",
    "period_from_day": "", "period_from_month": "", "period_from_year": "",
    "period_to_day": "", "period_to_month": "", "period_to_year": "",
    "full_or_part_time": "full",  # "full" or "part"
}


def all_in_scope_field_ids():
    """
    Returns the full set of field_ids this script is ever responsible for (identification,
    Summary of Projects x10, Summary of Experience grid). Used to explicitly blank out every
    in-scope field before applying real values, so stale data from a previous fill of the same
    PDF (e.g. a prior real submission used as the form template) never silently survives into a
    new draft. Out-of-scope fields (declarations, association-use-only, and page 5 unless backlog
    auto-fill is enabled) are NOT included here and are never touched by this script.
    """
    ids = set(fmap.IDENTIFICATION_FIELDS.values())
    ids.add(fmap.FULL_TIME_CHECKBOX_FIELD)
    ids.add(fmap.PART_TIME_CHECKBOX_FIELD)

    for slot in range(1, 11):
        ids.update(fmap.project_field_names(slot).values())

    for cat in range(1, 18):
        for col in range(1, 11):
            ids.add(fmap.hours_cell_field_name(cat, col))
        ids.add(fmap.category_row_total_field_name(cat))
        for col in range(1, 11):
            ids.add(fmap.subtotal_cell_field_name(cat, col))
        ids.add(fmap.section_subtotal_grand_total_field_name(cat))

    for col in range(1, 11):
        ids.add(fmap.project_grand_total_field_name(col))
    ids.add(fmap.OVERALL_GRAND_TOTAL_FIELD)

    # Backlog-period fields (page 5) -- in scope only when the optional backlog auto-fill is enabled,
    # so a non-backlog period explicitly clears them the same way every other in-scope field does.
    if BACKLOG_CUTOFF_DATE:
        ids.update(fmap.COMMENTS_FIELDS)
        ids.add(fmap.MENTOR_DECLARATION_NAME_FIELD)

    return ids


def is_backlog_period(identification, warnings):
    """True when backlog auto-fill is enabled and the period ends before backlog_cutoff_date."""
    if not BACKLOG_CUTOFF_DATE:
        return False
    try:
        cutoff = date.fromisoformat(str(BACKLOG_CUTOFF_DATE))
    except ValueError:
        warnings.append(f"Setting backlog_cutoff_date '{BACKLOG_CUTOFF_DATE}' is not YYYY-MM-DD -- backlog auto-fill skipped.")
        return False
    y, m, d = (identification.get(k, "") for k in ("period_to_year", "period_to_month", "period_to_day"))
    try:
        period_to = date(int(y), int(m), int(d))
    except (TypeError, ValueError):
        warnings.append("Period end date missing/invalid in identification.json -- backlog auto-fill skipped.")
        return False
    return period_to < cutoff


def build_field_values(grid, metadata, identification, content=None, column_to_global=None):
    """column_to_global: {local grid column: global project number} from split_multipage.py's
    manifest for this page. None means single-page (each column is its own global number)."""
    values = []
    warnings = []
    written_fields = set()

    def global_number(col):
        return column_to_global.get(col, col) if column_to_global else col

    def add(field_id, value, page, description):
        values.append({"field_id": field_id, "page": page, "value": value, "description": description})
        written_fields.add(field_id)


    # --- Page 1: Identification ---
    for meaning, field_id in fmap.IDENTIFICATION_FIELDS.items():
        if meaning in identification and identification[meaning] != "":
            add(field_id, identification[meaning], 1, f"Identification: {meaning}")

    ft_or_pt = identification.get("full_or_part_time", "").lower()
    if ft_or_pt == "full":
        add(fmap.FULL_TIME_CHECKBOX_FIELD, fmap.CHECKBOX_CHECKED_VALUE, 1, "Full-time Experience checkbox")
    elif ft_or_pt == "part":
        add(fmap.PART_TIME_CHECKBOX_FIELD, fmap.CHECKBOX_CHECKED_VALUE, 1, "Part-time Experience checkbox")
    elif ft_or_pt:
        warnings.append(f"full_or_part_time value '{ft_or_pt}' not recognized (expected 'full' or 'part') -- checkbox left unset.")

    # --- Optional backlog-period auto-fill: Mentor Identification, Comments by Employer, Mentor
    # Declaration (settings backlog_cutoff_date; off when null) ---
    if is_backlog_period(identification, warnings):
        mentor_surname_field = fmap.IDENTIFICATION_FIELDS["mentor_surname"]
        values[:] = [v for v in values if v["field_id"] != mentor_surname_field]  # backlog text wins
        add(mentor_surname_field, BACKLOG_TEXT, 1, "Mentor Identification (backlog period)")
        for q_field in fmap.COMMENTS_FIELDS:
            add(q_field, BACKLOG_TEXT, 5, "Comments by Employer (backlog period)")
        add(fmap.MENTOR_DECLARATION_NAME_FIELD, BACKLOG_TEXT, 5, "Mentor Declaration name (backlog period)")

    # --- Page 2: Role of Intern / "Project(s):" narrative synopsis ---
    # Only filled when --content is supplied (needs each project's project_brief text): the header
    # line from settings role_of_intern_header, then "(N) <name>\n<brief>" per project.
    if content and content.get("projects"):
        header = ROLE_OF_INTERN_HEADER
        entries = []
        page_numbers = None
        if column_to_global:
            # Multi-page: each sheet's synopsis lists only the projects on that sheet.
            page_numbers = {global_number(p["column"]) for p in grid["projects"]}
        for cp in content["projects"]:
            if page_numbers is not None and cp.get("number") not in page_numbers:
                continue
            brief = cp.get("project_brief")
            if not brief:
                warnings.append(f"Project '{cp.get('name')}' has no project_brief -- skipped in the Role of Intern synopsis (pre-existing data gap, not invented here).")
                continue
            entries.append(f"({cp['number']}) {cp['name']}\n{brief}")
        if entries:
            add(fmap.ROLE_OF_INTERN_FIELD, header + "\n\n" + "\n\n".join(entries), 2, "Role of Intern / Project(s) synopsis")

    # --- Page 3: Summary of Projects ---
    projects = grid["projects"]  # [{"column": 1, "name": "..."}, ...]
    if len(projects) > 10:
        raise SystemExit(f"{len(projects)} projects in grid, but the form only supports 10 project slots.")

    content_projects_by_number = {}
    if content:
        content_projects_by_number = {cp["number"]: cp for cp in content.get("projects", []) if "number" in cp}

    for p in projects:
        slot = p["column"]
        number = global_number(slot)  # == slot on page 1 / single-page; 11, 12... on page 2+
        grid_name = p["name"]  # metadata.json is keyed by this -- the grid/Project-Metadata name
        display_name = grid_name
        content_project = content_projects_by_number.get(number)
        if content_project and content_project.get("name"):
            # content.json is the hand-edited docx source -- use its name for the
            # field written to the form, so the docx and this numeric form can never drift apart on
            # a project's display name again. metadata.json lookup below still uses grid_name --
            # metadata.json is keyed by the original/short name, not content.json's expanded one.
            display_name = content_project["name"]
        elif content is not None:
            warnings.append(f"No content.json project found for project {number} (slot {slot}, '{grid_name}') -- Summary of Projects table falls back to the grid's own name; check for a docx/PDF naming drift.")
        if number != slot:
            # The form's printed column numbers are 1-10; continuation sheets carry the global
            # number in the name itself so project 11 isn't read as a second "project 1".
            display_name = f"({number}) {display_name}"
        names = fmap.project_field_names(slot)
        add(names["project_name"], display_name, 3, f"Project {number} name")
        meta = metadata.get(grid_name, {})
        if not meta:
            warnings.append(f"No metadata provided for project '{grid_name}' -- Summary of Projects row will be mostly blank.")
        for meta_key, field_meaning in [
            ("location", "location"), ("project_type", "project_type"), ("occupancy", "occupancy"),
            ("gross_floor_area", "gross_floor_area"), ("budget", "budget"), ("storeys", "storeys"),
        ]:
            val = meta.get(meta_key)
            if val:
                add(names[field_meaning], val, 3, f"Project {number} {meta_key}")

    # --- Page 4: Summary of Experience hours grid ---
    for row in grid["category_rows"]:
        cat_num = row["category_number"]
        for slot_str, hours in row["hours_by_project_column"].items():
            slot = int(slot_str)
            if hours and hours > 0:
                field_id = fmap.hours_cell_field_name(cat_num, slot)
                add(field_id, f"{hours:.2f}", 4, f"Category {cat_num} ({row['category_name']}) x Project {slot} hours")
        if row["row_total"] and row["row_total"] > 0:
            add(fmap.category_row_total_field_name(cat_num), f"{row['row_total']:.2f}", 4,
                f"Category {cat_num} row total")

    # Subtotal rows (one cell per project column, per section) + section grand totals
    for section, cats in [("A", range(1, 13)), ("B", range(13, 16)), ("C", (16, 17))]:
        section_cats = list(cats)
        subtotal_by_col = {col: 0.0 for col in range(1, len(projects) + 1)}
        for row in grid["category_rows"]:
            if row["category_number"] in section_cats:
                for slot_str, hours in row["hours_by_project_column"].items():
                    subtotal_by_col[int(slot_str)] += hours
        any_cat_in_section = section_cats[0]
        for col, total in subtotal_by_col.items():
            if total > 0:
                add(fmap.subtotal_cell_field_name(any_cat_in_section, col), f"{total:.2f}", 4,
                    f"Section {section} subtotal x Project {col}")
        section_total = grid["subtotals"].get(section, 0.0)
        if section_total > 0:
            add(fmap.section_subtotal_grand_total_field_name(any_cat_in_section), f"{section_total:.2f}", 4,
                f"Section {section} overall subtotal")

    # Grand totals
    for col_str, total in grid["project_totals"].items():
        col = int(col_str)
        if total > 0:
            add(fmap.project_grand_total_field_name(col), f"{total:.2f}", 4, f"Project {col} grand total")
    if grid["grand_total"] > 0:
        add(fmap.OVERALL_GRAND_TOTAL_FIELD, f"{grid['grand_total']:.2f}", 4, "Overall grand total")

    # --- Explicitly blank every in-scope field not otherwise written ---
    # This is mandatory, not optional: the source PDF used as the fill template may be a real
    # prior submission (this happens in practice) rather than a
    # truly blank form. Without this pass, any in-scope field this run didn't supply a value for
    # would silently retain whatever was already in the PDF, leaking stale data into a new draft.
    page_lookup = _build_field_page_lookup()
    for field_id in all_in_scope_field_ids():
        if field_id in written_fields:
            continue
        if field_id in (fmap.FULL_TIME_CHECKBOX_FIELD, fmap.PART_TIME_CHECKBOX_FIELD):
            add(field_id, fmap.CHECKBOX_UNCHECKED_VALUE, 1, "Explicitly cleared (not selected)")
        else:
            add(field_id, "", page_lookup.get(field_id, 1), "Explicitly cleared (no value for this run)")

    return values, warnings


def _build_field_page_lookup():
    """Maps every in-scope field_id to its page number, for the blanking pass above."""
    lookup = {}
    for field_id in fmap.IDENTIFICATION_FIELDS.values():
        lookup[field_id] = 1
    lookup[fmap.FULL_TIME_CHECKBOX_FIELD] = 1
    lookup[fmap.PART_TIME_CHECKBOX_FIELD] = 1
    for slot in range(1, 11):
        for field_id in fmap.project_field_names(slot).values():
            lookup[field_id] = 3
    for cat in range(1, 18):
        for col in range(1, 11):
            lookup[fmap.hours_cell_field_name(cat, col)] = 4
        lookup[fmap.category_row_total_field_name(cat)] = 4
        for col in range(1, 11):
            lookup[fmap.subtotal_cell_field_name(cat, col)] = 4
        lookup[fmap.section_subtotal_grand_total_field_name(cat)] = 4
    for col in range(1, 11):
        lookup[fmap.project_grand_total_field_name(col)] = 4
    lookup[fmap.OVERALL_GRAND_TOTAL_FIELD] = 4
    for field_id in fmap.COMMENTS_FIELDS:
        lookup[field_id] = 5
    lookup[fmap.MENTOR_DECLARATION_NAME_FIELD] = 5
    return lookup


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("grid_json", help="Path to build_hours_grid.py's output JSON")
    parser.add_argument("metadata_json", help="Path to project metadata JSON")
    parser.add_argument("identification_json", help="Path to identification info JSON")
    parser.add_argument("--out", required=True, help="Path to write field_values.json")
    parser.add_argument("--content", default=None, help="Path to content.json (docx source) -- enables Role of Intern auto-fill and project-name consistency with the docx (see module docstring)")
    parser.add_argument("--manifest", default=None, help="split_multipage.py's page manifest JSON -- maps this page's local columns to global project numbers (requires --page)")
    parser.add_argument("--page", type=int, default=None, help="Page number within --manifest that grid_json was built from")
    args = parser.parse_args()
    if (args.manifest is None) != (args.page is None):
        parser.error("--manifest and --page must be given together")

    # encoding="utf-8" is required on every read here -- Windows' default codec (cp1252-ish)
    # otherwise silently mangles any non-ASCII character (em dashes, curly quotes, etc.) into
    # mojibake, which then propagates into field_values.json and the filled PDF itself (e.g. em
    # dashes turning into "â€"").
    with open(args.grid_json, encoding="utf-8") as f:
        grid = json.load(f)
    with open(args.metadata_json, encoding="utf-8") as f:
        metadata = json.load(f)
    with open(args.identification_json, encoding="utf-8") as f:
        identification = json.load(f)
    content = None
    if args.content:
        with open(args.content, encoding="utf-8") as f:
            content = json.load(f)

    column_to_global = None
    manifest_warnings = []
    if args.manifest:
        with open(args.manifest, encoding="utf-8") as f:
            manifest = json.load(f)
        page = next((p for p in manifest.get("pages", []) if p.get("page_number") == args.page), None)
        if page is None:
            raise SystemExit(f"Page {args.page} not found in manifest {args.manifest}.")
        column_to_global = {int(k): int(v) for k, v in page["local_column_to_global_number"].items()}
        # The map is only valid if the grid's columns came out in the manifest's project order.
        expected = page.get("project_names_in_order", [])
        for p in grid["projects"]:
            col = p["column"]
            if col > len(expected) or expected[col - 1] != p["name"]:
                manifest_warnings.append(
                    f"Grid column {col} is '{p['name']}' but the manifest expects "
                    f"'{expected[col - 1] if col <= len(expected) else '(none)'}' -- page CSV row order "
                    f"doesn't match the manifest, so global numbering for this page is unreliable."
                )

    values, warnings = build_field_values(grid, metadata, identification, content, column_to_global)
    warnings = manifest_warnings + warnings

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2)

    print(f"Wrote {len(values)} field values to {args.out}", file=sys.stderr)
    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
