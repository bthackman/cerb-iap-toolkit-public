# AGENTS.md — instructions for the AI assistant

You are helping an architectural intern set up and run the **CERB / IAP Toolkit**: Airtable time
logs → a draft Canadian Experience Record Book (CERB) submission (filled official PDF form + a
"Project Descriptions — Role of Intern" Word document).

This file is read automatically by Claude Code (via `CLAUDE.md`), GitHub Copilot
(via `.github/copilot-instructions.md`) and most other coding agents. The human's own guide is
[`docs/HOW-TO-USE.md`](docs/HOW-TO-USE.md) — keep your explanations consistent with it.

---

## 0. Non-negotiable rules

1. **Never hand-tally hours.** Every number on the form comes from the scripts
   (`build_hours_grid.py` via `run_period.py`). If a total looks wrong, fix the data or the code and
   re-run — never type a number into `content.json` or the PDF to make it agree.
2. **Never invent experience.** Every bullet must be supported by the user's own time-entry
   descriptions for that project and category. If a row can't be mapped, flag it (see §4) or ask.
3. **Confidentiality.** Never name clients, consultants, contractors, tenants or colleagues in the
   narrative unless the user explicitly says that name may appear. Use role terms ("the client",
   "the structural consultant", "a retail tenant"). Spell acronyms out.
4. **One submission period per run.** Prepare → draft → user review → clean pass → reviewer pass.
   Stop for the user between draft and clean pass. Never batch several periods into one pass.
5. **No writes to Airtable unless the user explicitly asks** (the logger skill in §6 is the only
   write path, and it re-verifies counts after every write).
6. **Never commit secrets or personal data:** `pipeline/.env`, `pipeline/settings.json`,
   `pipeline/identification.json`, `exports/`, and the official form PDF are git-ignored on purpose.
   Don't force-add them. If the user forks this repo publicly, warn them before pushing personal data.
7. **The official CERB PDF is not in this repo** (it belongs to the licensing authorities). The user
   supplies it — see [`form/README.md`](form/README.md).

## 1. Repository map

| Path | What it is |
|---|---|
| `pipeline/run_period.py` | **Main entry point.** `prepare` (data → hours grid) and `build` (grid + narrative → PDF, docx, meta, dashboard). |
| `pipeline/settings.example.json` → `settings.json` | Per-user settings: track, jurisdiction, period length/cap, backlog auto-fill, internal buckets, form path. Documented in `pipeline/README.md`. |
| `pipeline/*.py` | Individual steps (fetch, filter, metadata conversion, fill PDF, meta, dashboard) — each runnable on its own. |
| `tools/airtable-adapter/` | Airtable records → `PROJECT,CATEGORY,HOURS,NOTE DESCRIPTION` CSV; multi-sheet splitter (max 10 projects per form sheet). |
| `tools/docx-builder/build.py` | Builds the Project Descriptions `.docx` from `content.json`; warns if its hours disagree with the grid. |
| `skills/cerb-iap-architecture-internship/` | **Knowledge**: the 17 experience categories, hour minimums, IAP process, how to write good entries. Read before writing any bullet. |
| `skills/cerb-submission-builder/` | **Workflow**: the step-by-step procedure for one period, PDF field map, docx template. |
| `skills/cerb-submission-reviewer/` | **Critique**: simulates the supervising architect + regulator review. Run on every clean pass. |
| `skills/cerb-airtable-logger/` | **Optional**: turns pasted/OCR'd timesheet text into validated Airtable rows (backfilling old timesheets). |
| `airtable/AIRTABLE-SCHEMA.md` | The two-table base the code expects. Field names are load-bearing. |
| `examples/` | Fictional fixtures for a full offline test run. |
| `config/abbreviations.md` | The user's own acronym glossary and project display-name aliases. |

The `skills/*/SKILL.md` files are plain Markdown. **Claude Code** users can optionally copy or link
each `skills/<name>/` folder into `.claude/skills/<name>/` so they load as native skills.
**Copilot** users: attach the relevant `SKILL.md` and its `references/` files as context
(`#file:`) when doing that step — they are written to be read directly.

## 2. First-time setup (walk the user through this)

Do these in order, confirming each before moving on. Explain *why* briefly; the user is an
architect, not necessarily a programmer.

1. **Python 3.9+** — check `python --version`. Create a virtual environment and
   `pip install -r requirements.txt`.
2. **Offline smoke test (no accounts needed):**
   ```
   python pipeline/run_period.py prepare --start 2027-01-01 --offline examples/raw_records.json --offline-metadata examples/project_metadata.json
   cp examples/content.example.json exports/2027-02-19/content.json
   python pipeline/run_period.py build --end 2027-02-19
   ```
   Expect 3 projects / **72.50 h**. The build reports the form PDF is missing until step 5 — the docx,
   `meta.json` and dashboard still generate. Delete `exports/2027-02-19/` afterwards.
3. **Airtable** — copy the template base (link in `README.md`) or build it from
   `airtable/AIRTABLE-SCHEMA.md`. Create a personal access token scoped to that one base
   (`data.records:read`, `schema.bases:read`, plus `data.records:write` only if they'll use the logger).
   Copy `pipeline/.env.example` → `pipeline/.env`, fill `AIRTABLE_TOKEN` and `AIRTABLE_BASE_ID`.
   Verify with `python pipeline/test_airtable.py`.
4. **Settings** — copy `pipeline/settings.example.json` → `pipeline/settings.json`. Ask the user:
   standard (3,720 h) or Syllabus (9,800 h) track? Which provincial regulator? Do they need backlog
   auto-fill (only if their regulator accepts retroactive periods that way)? What are their firm's
   internal time buckets? Edit accordingly.
5. **Official form** — have the user download the current fillable CERB PDF and save it as
   `form/CERB_fillable_form.pdf`. If their edition differs from the 2020 edition, list its fields
   (command in `form/README.md`) and compare against
   `skills/cerb-submission-builder/references/pdf-form-fields.md` before trusting a fill; update
   `scripts/cerb_pdf_field_map.py` if names changed.
6. **Identification** — copy `pipeline/identification.example.json` → `pipeline/identification.json`
   and fill it with the user (intern, employer, supervisor, mentor). Period dates are filled per run.
7. **Abbreviations** — help the user start `config/abbreviations.md` with their firm's and projects'
   acronyms and the display name each project should carry on the CERB.
8. **Project metadata** — in Airtable's `Project Metadata` table, every real project needs Location,
   Project Type, Occupancy, GFA, Budget, Storeys (`n/a` is a valid answer). Check internal buckets
   have `Non-Project / Internal` ticked.

## 3. Running one submission period

Follow `skills/cerb-submission-builder/SKILL.md`; this is the short version.

1. **Prepare**: `python pipeline/run_period.py prepare --start YYYY-MM-DD [--end YYYY-MM-DD]`.
   Without `--end`, the period ends at `period_months` or `period_hours_cap` eligible hours, whichever
   comes first. Read the summary aloud to the user: projects and hours per sheet, excluded rows
   (especially *real projects with no CERB Section* — offer to help categorize those in Airtable and
   re-run). If more than 10 projects, discuss `--drop-project` (thin projects under
   `thin_project_hours`) or continuation sheets (numbered 11, 12, 13…, handled automatically).
2. **Narrative-writing step** — see §4. You write `exports/<end>/content.json`.
3. **Build**: `python pipeline/run_period.py build --end YYYY-MM-DD`. Resolve every warning,
   especially "content.json hours differ from grid".
4. **Draft review** — summarize for the user: number of flagged (orange) bullets, excluded (red)
   rows, missing project metadata. **Stop and wait.**
5. **Clean pass** — apply their answers, remove resolved flags, rebuild.
6. **Reviewer pass** — run `skills/cerb-submission-reviewer/SKILL.md` against the clean draft and
   present its memo. If it says "needs revision", say so plainly.
7. **Finalize** — only when the user says the period is submitted/approved:
   `build --end … --final`.

## 4. Narrative-writing step (`content.json`)

Inputs: `exports/<end>/work/cerb_input.csv` (every eligible row: project, category, hours, note),
`exports/<end>/work/grid_*.json`, `page_manifest.json` (global project numbers), and the
`Project Metadata` values. Before writing, read:

- `skills/cerb-iap-architecture-internship/references/experience-categories.md`
- `skills/cerb-iap-architecture-internship/references/writing-good-entries.md`
- `skills/cerb-submission-builder/references/docx-output-template.md`
- `config/abbreviations.md`

Shape — copy `examples/content.example.json` exactly:

- `title`, `subtitle` (intern name + period), `note` (draft legend).
- `projects[]` in global project-number order, each with `number`, `name` (display name — the same
  string everywhere), `project_type`, `occupancy`, **`project_brief` (every project, no exceptions)**,
  and `categories[]`.
- `categories[]` in **ascending category number (1 → 17)**, each with `number`, `name`, `hours`
  (**copied from the grid, never computed by you**) and `bullets[]`.
- A bullet is a string, or `{"text": …, "flag": "…"}` (orange: a best guess the user must confirm)
  or `{"text": …, "exclude": "…"}` (red: a row you believe isn't eligible architectural experience).

Writing rules (details in `writing-good-entries.md`): lead with the IAP manual's own activity
language for that category, then graft in the project specifics from the notes; synthesize a small
set of bullets per category (roughly 2–6, more hours ≠ more bullets); past tense, intern's role
("Assisted in…", "Prepared…", "Coordinated…"); no client/consultant names; acronyms spelled out;
nothing the notes don't support.

## 5. Common changes the user may ask for

| Request | Where |
|---|---|
| Different period length or hours cap | `settings.json` → `period_months`, `period_hours_cap` |
| Syllabus vs standard targets | `settings.json` → `track` (minimum tables live in `pipeline/settings.py`) |
| Rename a project on the CERB only | Record the display name in `config/abbreviations.md`, use it as `content.json` `name` (the PDF reads the same string) — never rename in Airtable just for display |
| Combine two Airtable projects on the CERB | `prepare --merge "SOURCE=TARGET"` (presentation only; Airtable untouched) |
| Leave a project out | Tick `Non-Project / Internal` in Airtable (permanent) or `prepare --drop-project` (this period only) |
| New edition of the form | `form/README.md` → field listing → update `cerb_pdf_field_map.py` |
| Dashboard / Markdown notes into Obsidian | set `CERB_VAULT_DIR` in `pipeline/.env` (optional) |

## 6. Logging hours from old timesheets (optional)

`skills/cerb-airtable-logger/SKILL.md` parses pasted or OCR'd timesheet text into staged rows,
validates them (`validate_entries.py`), optionally suggests a CERB Section
(`suggest_cerb_sections.py`), and writes them (`airtable_write.py`) **only after the user approves
the staged batch**. After any multi-batch write, re-query the live record count and total hours and
compare with the staged payload before declaring success. Read
`references/rough-data-review-methodology.md` first — it lists the failure modes that actually
happened (duplicate batches, wrong project matches, stale date headers).

## 7. If you are rebuilding instead of reusing

If the user wants it in another stack (e.g. Power Automate, a web app, Excel), keep these invariants
— they are what the scripts encode:

- Airtable `Hours` is a duration in **seconds**; divide by 3600; the form shows 2 decimals.
- A row counts only if it has exactly one `CERB Section` and its project is not
  `Non-Project / Internal`. Report excluded rows; never drop silently.
- Category number = the integer after the letter in the section label (`A8:` → 8).
- One form sheet holds **10 projects**; extra projects continue on additional sheets numbered 11+.
- Project order on the form = descending hours; categories inside a project ascend 1 → 17.
- Period = 6 months (end = day before the 6-month mark) or 1,000 eligible hours, whichever first.
- The PDF fill must clear every in-scope field it doesn't set (templates can contain stale data),
  and must never touch the declaration/signature fields.
- The docx and the PDF must read the same project display name and hours.

Acceptance test: the offline example in §2 must produce 72.50 h across 3 projects, a filled
5-page PDF and a docx with categories in ascending order.
