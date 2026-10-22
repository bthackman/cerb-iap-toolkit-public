# Pipeline

These scripts run the toolkit from start to finish. They pull your time log from Airtable, build
the hours grid and fill the official CERB PDF form. They also build the "Project Descriptions —
Role of Intern" .docx from the narrative your AI assistant writes, then track your progress across
periods.

All commands run from the repository root. `-I` (isolated mode) is recommended.

## Setup (once)

1. `pip install -r requirements.txt`
2. Build the Airtable base described in [`airtable/AIRTABLE-SCHEMA.md`](../airtable/AIRTABLE-SCHEMA.md).
3. Copy `pipeline/.env.example` to `pipeline/.env` and add `AIRTABLE_TOKEN` and
   `AIRTABLE_BASE_ID`. Never commit `.env`. Then check the connection with
   `python -I pipeline/test_airtable.py`, which only reads the base.
4. Copy `pipeline/identification.example.json` to `pipeline/identification.json` and fill in
   your details: intern, employer, supervisor and mentor. Leave the `period_*` fields blank,
   because they are filled in for each period.
5. Copy `pipeline/settings.example.json` to `pipeline/settings.json` and adjust it (see below).
6. Download the fillable CERB form to `form/CERB_fillable_form.pdf`. See
   [`form/README.md`](../form/README.md).

`.gitignore` already excludes `.env`, `settings.json`, `identification.json`, Airtable exports,
`exports/` and the form PDF.

## Try it offline first (no Airtable, fictional data)

```
python -I pipeline/run_period.py prepare --start 2027-01-01 --offline examples/raw_records.json --offline-metadata examples/project_metadata.json
copy examples\content.example.json exports\2027-02-19\content.json      (macOS/Linux: cp examples/content.example.json exports/2027-02-19/content.json)
python -I pipeline/run_period.py build --end 2027-02-19
```

The example data puts 72.50 eligible hours across three fictional projects. Without
`identification.json`, an offline run uses the fictional `examples/identification.example.json`.
Delete `exports/2027-02-19/` when you're done.

## Building a real period

```
python -I pipeline/run_period.py prepare --start YYYY-MM-DD [--end YYYY-MM-DD]
        [--offline RAW.json --offline-metadata PM.json] [--identification PATH]
        [--drop-project "Name"]... [--merge "Source Name=Target Name"]...
# -> have your AI assistant write exports/<end>/content.json (see AGENTS.md)
python -I pipeline/run_period.py build --end YYYY-MM-DD [--final] [--form PATH] [--content PATH] [--out-dir DIR]
```

**`prepare`** runs these steps:

1. Fetches both Airtable tables (unless `--offline`).
2. Filters the records to the period.
3. Converts them to the grid CSV and reports the excluded rows.
4. Converts Project Metadata.
5. Writes this period's `identification.json`.
6. Splits the projects into form sheets, largest first, with `max_projects_per_page` per sheet.
   Sheet 2 continues the numbering at 11, 12, 13 and so on.
7. Computes one hours grid per sheet.

If you leave out `--end`, the period runs to the last logged entry within `period_months` of
`--start`. It stops earlier if it reaches `period_hours_cap` eligible hours. The summary prints
each project's number and hours, rows that need attention, and the next step.

* `--drop-project "Name"` leaves a project out of this period only, and can be repeated. Your
  hours stay in Airtable. To exclude a project permanently, tick **Non-Project / Internal** on its
  Project Metadata row.
* `--merge "A=B"` reports A's rows under B for this period only. Use it for presentation-only
  merges, such as one project billed under two codes. Airtable is never changed.

**`build`** runs these steps:

1. Generates the PDF field values for each sheet.
2. Fills the form for each sheet: `CERB_Page1_DRAFT_<end>.pdf`, then `_page2.pdf` and so on.
3. Builds `CERB_Project_Descriptions_DRAFT_<end>.docx`. It warns if the hours in `content.json`
   don't match the grid.
4. Writes `exports/<end>/meta.json`.
5. Refreshes `exports/dashboard.html`.

If the form PDF is missing, `build` still produces the docx, meta.json and dashboard. It then
exits with a message pointing to `form/README.md`. `--final` marks the period FINAL. The next
period's default start is the day after the last FINAL period.

### Where things go

```
exports/<end>/content.json            narrative (written by your AI assistant; build snapshots it here)
exports/<end>/CERB_Page1_DRAFT_<end>[_pageN].pdf
exports/<end>/CERB_Project_Descriptions_DRAFT_<end>.docx
exports/<end>/meta.json               hours, category totals, draft/final status
exports/<end>/work/                   raw_records_filtered.json, cerb_input.csv, adapter_report.json,
                                      metadata.json, identification.json, page_N.csv,
                                      page_manifest.json, grid_N.json, field_values_N.json
exports/dashboard.html                progress across all periods
```

## Settings (`pipeline/settings.json`)

`settings.example.json` provides the defaults. Your `settings.json` only needs the keys you change.
To use a different file, set the `CERB_SETTINGS` environment variable to its path.

| Key | Default | Used for |
|---|---|---|
| `track` | `"standard"` | `"standard"` (3,720 h IAP) or `"syllabus"` (9,800 h RAIC Syllabus). Sets the dashboard targets and the category-balance tie-break in `suggest_cerb_sections.py`. |
| `jurisdiction` | `"Alberta Association of Architects (AAA)"` | Your regulator. Used for the reviewer persona and the dashboard subtitle. |
| `period_months` | `6` | Default period length. |
| `period_hours_cap` | `1000` | A period ends early once it reaches this many eligible hours. |
| `backlog_cutoff_date` | `null` | Optional. `"YYYY-MM-DD"` turns on backlog auto-fill for periods ending before that date. `backlog_text` then goes into the mentor surname, the 4 Comments by Employer boxes and the Mentor Declaration name. With `null`, page 5 is never touched. |
| `backlog_text` | `"N/A BACKLOG HOURS"` | Text for the backlog auto-fill. |
| `internal_bucket_names` | `["VACATION","SICK","STAT","ADMIN","TEAM MEETING","TRAINING / EVENT"]` | Project Metadata names for non-project time. These never get a CERB Section suggestion, and the exclusion report lists them separately. |
| `thin_project_hours` | `10` | When a period needs more than one sheet, `prepare` lists projects under this many hours as candidates for `--drop-project`. |
| `role_of_intern_header` | (see file) | First line of the form's page-2 Role of Intern synopsis. |
| `max_projects_per_page` | `10` | Projects per form sheet, from 1 to 10. |
| `form_pdf` | `"form/CERB_fillable_form.pdf"` | The fillable form. Can be overridden with `CERB_FORM_PDF` or `build --form`. |
| `exports_dir` | `"exports"` | Output root, relative to the repo or absolute. |

## The individual scripts (step by step)

`run_period.py` only calls these scripts in order, so each one still works on its own. Paths are
relative to the repo root.

1. `pipeline/fetch_records.py` pulls the Time Tracking table into `pipeline/raw_records.json`.
2. `pipeline/fetch_project_metadata.py` pulls the Project Metadata table into
   `pipeline/project_metadata.json`.
3. `pipeline/filter_by_date.py [--start --end --records --project-metadata]` writes
   `exports/<end>/work/raw_records_filtered.json`.
4. `tools/airtable-adapter/airtable_to_cerb_csv.py RECORDS PROJECT_METADATA OUT.csv [--report R.json]`
   converts the records to the grid CSV.
5. `pipeline/metadata_from_airtable.py project_metadata.json metadata.json` writes the Summary of
   Projects details.
6. `tools/airtable-adapter/split_multipage.py IN.csv --out-prefix .../page` writes
   `page_N.csv` and `page_manifest.json`.
7. `skills/cerb-submission-builder/scripts/build_hours_grid.py page_N.csv --out grid_N.json`
   computes the hours grid, the arithmetic source of truth.
8. Your AI assistant writes `content.json`, following
   `skills/cerb-submission-builder/SKILL.md` and `references/docx-output-template.md`.
9. `skills/cerb-submission-builder/scripts/generate_pdf_field_values.py grid_N.json metadata.json identification.json --out field_values_N.json --content content.json --manifest page_manifest.json --page N`
   generates the PDF field values.
10. `pipeline/fill_fillable_fields.py FORM.pdf field_values_N.json [--out OUT.pdf]` fills the form.
11. `tools/docx-builder/build.py --content content.json [--identification ...] [--grid ...] [--out-dir ...]`
    builds the docx.
12. `pipeline/generate_meta.py --end-date <end> [--final|--draft]` writes `meta.json`.
13. `pipeline/generate_dashboard.py` refreshes `exports/dashboard.html`.

Helpers:

* `period_paths.py` holds the per-period folder logic.
* `settings.py` loads the settings and the per-category minimum-hour tables for both tracks.
* `plan_backlog_periods.py [--start] [--until]` prints the period sequence to use when you're
  catching up on several unsubmitted periods.

### Optional: Markdown notes

Set `CERB_VAULT_DIR` in your environment or in `pipeline/.env` to a notes folder, such as an
Obsidian vault. `generate_dashboard.py` then also writes a `CERB Progress.md` summary there.
`content_to_vault.py --content ... [--subdir CERB] [--tags "#CERB"]` exports each period's
narrative as Markdown. If the variable is unset, both steps are skipped.
