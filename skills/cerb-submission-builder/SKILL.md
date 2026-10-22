---
name: cerb-submission-builder
description: Generates a draft CERB (Canadian Experience Record Book) submission package -- project description bullets (docx), the Summary of Experience hours grid, and the Summary of Projects table (filled official PDF) -- from logged hours/project/category/note data in the user's Airtable base. Use this skill when the user asks to draft, generate, or build a CERB submission, "write up my hours for this period," "turn my logged hours into a CERB entry," or similar. Depends on the cerb-iap-architecture-internship knowledge skill for category definitions, hour requirements, and the bullet-writing voice/logic -- load that skill's references alongside this one rather than duplicating them. Project metadata (Location/Type/Occupancy/GFA/Budget/Storeys) comes from the "Project Metadata" Airtable table rather than being re-asked every cycle.
---

# CERB Submission Builder

Turns logged architectural-experience data into a draft CERB submission package: project description
bullets (a standalone docx attachment) and the filled official PDF form (identification, Summary of
Projects, Summary of Experience grid). This skill is the **workflow** layer; it depends on
`cerb-iap-architecture-internship` (the knowledge skill) for *what the rules are* and *how to write a
good bullet* — load that skill's references as needed rather than re-deriving anything here.

The arithmetic and form-filling are done by scripts; the AI's job is the narrative (`content.json`) and
the judgment calls. The default path is the single entry point `pipeline/run_period.py`:

```
python -I pipeline/run_period.py prepare --start YYYY-MM-DD [--end YYYY-MM-DD]
        [--offline RAW.json --offline-metadata PM.json] [--identification PATH]
        [--drop-project "Name"]... [--merge "Source Name=Target Name"]...
# ... AI writes exports/<end>/content.json ...
python -I pipeline/run_period.py build --end YYYY-MM-DD [--final] [--form PATH] [--out-dir DIR]
```

Behaviour is configured in `pipeline/settings.json` (copy `pipeline/settings.example.json`): `track`,
`jurisdiction`, `period_months`, `period_hours_cap`, `backlog_cutoff_date`, `backlog_text`,
`internal_bucket_names`, `thin_project_hours`, `role_of_intern_header`, `max_projects_per_page`,
`form_pdf`, `exports_dir`. See `pipeline/README.md` for each key.

## Before starting: confirm scope

Ask the user (if not already clear) what period this submission covers. A period is normally
`period_months` long (default 6) and capped at `period_hours_cap` CERB-eligible hours (default 1,000) —
`prepare` computes the end date from `--start` if `--end` isn't given.

## Scope: exactly one period per run

Every run produces exactly one CERB submission period. This holds even when there's a queue of several
periods to build (e.g. historical backlog periods): build one period fully (through whatever stopping
point the user asked for — often just the draft pass, step 7), stop, and wait for the user's go-ahead
before starting the next. Never batch narrative generation, hours grids, or drafts for more than one
period into a single run.

## Step-by-step procedure

### 1. Load dependencies
Read (or confirm already loaded in context):
- `cerb-iap-architecture-internship/references/experience-categories.md` — category definitions and
  manual activity language (the bullet-writing voice source)
- `cerb-iap-architecture-internship/references/writing-good-entries.md` — the bullet-generation
  priority order, two-pass workflow, flag/exclude conventions, abbreviation rule, display-rename vs.
  merge rules. **Bullet generation must follow that file exactly** — it is not repeated here.
- `config/abbreviations.local.md` if it exists, else `config/abbreviations.md` — the user's
  abbreviation glossary and project aliases
- `references/docx-output-template.md` (this skill) — the docx structure and `content.json` shape

### 2. Prepare the period's data
Run `python -I pipeline/run_period.py prepare --start YYYY-MM-DD [--end ...]`. It fetches records from
Airtable (or uses `--offline` fixtures), filters to the period, converts to the
`PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION` CSV, converts Project Metadata, splits into pages, and builds
the hours grid(s). Working files land in `exports/<end>/work/`: `raw_records_filtered.json`,
`cerb_input.csv`, `adapter_report.json`, `metadata.json`, `identification.json`, `page_N.csv`,
`page_manifest.json`, `grid_N.json`.

Read its printed summary and `adapter_report.json`. Rows with no CERB Section are excluded — tell the
user about any **real-project** rows excluded that way so they can categorize them in Airtable and
re-run. Rows linked to a `Non-Project / Internal` Project Metadata row never reach the CSV — that
checkbox covers internal buckets and also real projects the user chooses to leave out (e.g. work their
supervising architect can't sign off, such as projects outside the supervisor's registration
jurisdiction). This skill doesn't filter anything itself.

Step-by-step alternative (same result, one script at a time): `pipeline/fetch_records.py`,
`pipeline/fetch_project_metadata.py`, `pipeline/filter_by_date.py`,
`tools/airtable-adapter/airtable_to_cerb_csv.py`, `pipeline/metadata_from_airtable.py`,
`tools/airtable-adapter/split_multipage.py`, `scripts/build_hours_grid.py` — see `pipeline/README.md`.

**More than one page**: `prepare` splits by `max_projects_per_page` (≤10), largest-hours-first, and
page 2+ is renumbered 11, 12, 13… automatically. It also lists projects under `thin_project_hours`; ask
the user whether to keep them or drop them for this period with `--drop-project "Name"` (hours stay in
Airtable). **Presentation-only merges** (two Airtable projects that are one CERB project) are applied
with `--merge "Source=Target"` before the grid is computed. Re-run `prepare` after any such change.

### 3. Resolve Summary of Projects metadata
For each project the form needs **Location, Project Type, Occupancy, Gross Floor Area, Budget, Number
of Storeys**. These come from the Project Metadata table, converted into `exports/<end>/work/metadata.json`
by `prepare`. **Use what's there — don't re-ask.** `n/a` is a valid, complete answer (master plans,
hourly work); only a **blank** field is missing.

For blank fields, batch one question listing every project and missing field, and suggest the user fill
them in Airtable (so they're never re-asked). **Answering must never block progress** — blank fields stay
blank in the draft and get asked again next cycle; skipping once doesn't mean "never applies."

### 4. Generate project description bullets → `content.json`
Write `exports/<end>/content.json` (shape in `references/docx-output-template.md`). For each project
(numbered in the grid's global order: page 1 columns 1–10, page 2 continuing at 11…), apply the full
priority order from `writing-good-entries.md`: manual-anchored phrasing, project specifics grafted in,
reusable closing bullets, ask only on genuine unmappability, flag soft ambiguity, exclude
confirmed-ineligible rows. Categories within a project in ascending category-number order; per-category
`hours` copied exactly from the grid. Every project gets a `project_brief`. Spell out every abbreviation;
genericize every company name.

Do not skip or compress this step even when many rows look similar — each row's note is the evidence for
its hours and deserves its own pass, not a bulk templated rewrite.

### 5. The hours grid is computed, never hand-tallied
`build_hours_grid.py` (run by `prepare`) is the arithmetic source of truth — never estimate totals. If
rows were confirmed ineligible in step 4, list them in an exclusion JSON and rebuild the grid with
`scripts/build_hours_grid.py --exclude-file` (or remove them at source and re-run `prepare`) so the grid
matches the narrative. Review the grid's `warnings` — a warning means a row was dropped, which must not
happen without the user knowing. Sanity-check one category against the CSV by hand before trusting it.

### 6. Build the outputs
Run `python -I pipeline/run_period.py build --end YYYY-MM-DD`. It generates PDF field values per page,
fills the PDF form from `form_pdf` (see `form/README.md` — the official form isn't bundled), builds the
docx with `tools/docx-builder/build.py` (which checks content.json hours against the grid and warns on any
mismatch — fix every warning), writes `meta.json`, and regenerates `exports/dashboard.html`.

**The docx is narrative only** — never put the hours grid in it; the grid's only home is the PDF (see
`docx-output-template.md`).

Check the outputs visually: open the docx in Word, and open the PDF (render pages to images if your
assistant can, otherwise in a PDF viewer) — at least the identification page and the hours grid page.
Field-name mapping errors are silent, so visual verification is the real check.

### 7. Deliver the draft pass and stop
Present the docx and PDF. Do not produce a "clean" version in the same turn. Summarize briefly what needs
the user's attention: how many flagged bullets, how many excluded rows, outstanding metadata. Wait for
the user's response.

### 8. Clean pass
Once the user responds, update `content.json`: incorporate corrections, remove flag/exclusion markup for
resolved items, rebuild the grid if exclusions changed, and re-run `build`. Only re-flag something if the
user's correction introduces a new ambiguity.

### 9. Reviewer critique pass (every clean pass)
Invoke `cerb-submission-reviewer` against the clean-pass draft. It simulates the critical read the draft
will get from the Supervising Architect and the jurisdiction reviewer. Present its review memo alongside
the draft. If its verdict is "needs revision," say so plainly rather than presenting the draft as done.

### 10. Finalize
When the user confirms the period has actually been submitted, run `build --end ... --final` (or
`pipeline/generate_meta.py --final`) so `meta.json` records it as final; the next period's default start
date is the day after the last final period.

## PDF form scope

`scripts/generate_pdf_field_values.py` fills only: page 1 identification (from
`exports/<end>/work/identification.json`, seeded from `pipeline/identification.json`), page 2 Role of
Intern synopsis (`role_of_intern_header` + each project's `project_brief`), page 3 Summary of Projects,
and the page 4 hours grid. Field names are in `references/pdf-form-fields.md` /
`scripts/cerb_pdf_field_map.py`.

**Always let the explicit-blanking pass run.** The PDF used as the template may not be genuinely blank
(a previous fill can be saved in it). The script clears every in-scope field it isn't given a value for so
stale data never survives into a new draft. Never bypass this.

**Backlog auto-fill is optional.** With `backlog_cutoff_date` set, periods ending before that date get
`backlog_text` (default "N/A BACKLOG HOURS") written into Mentor Identification's surname, the four
Comments by Employer fields, and the Mentor Declaration name field; for periods ending on/after the
cutoff those same page-5 fields are explicitly cleared. With `backlog_cutoff_date` null (the default),
page 5 is never touched. Signatures and declaration dates (pages 4–5) are always out of scope — never
filled, never cleared.

## Known limitations

- **Bullets are only as good as the notes.** Thin notes produce flagged or generic bullets — the fix is
  richer logging, not invention.
- **Ten projects per form page** (a hard limit of the official form). Multi-page periods are split and
  renumbered automatically; each page is its own filled PDF (`_page2`, `_page3`…).
- **Field map verified against one form edition** (see `references/pdf-form-fields.md`). If your
  jurisdiction's current form differs, check field names first (`form/README.md`).
