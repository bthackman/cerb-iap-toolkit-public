---
name: cerb-airtable-logger
description: Parses unstructured/freeform time-entry text (a single pasted line, a backlog dump, or an OCR'd timesheet PDF) and writes it as correctly structured records into the user's CERB Airtable base ("Time Tracking" table, linked to "Project Metadata"). Use this skill when the user pastes freeform hours notes (e.g. "2027-02-12 2Hr- Community Library | Worked on drawings"), asks to "log this into Airtable," "backfill my hours," or hands over a timesheet export/PDF to get into the live base. Depends on cerb-iap-architecture-internship for CERB Section category definitions — load its references/experience-categories.md alongside this one. Complements cerb-submission-builder, which builds a submission draft from the logged data; this skill is the write path into Airtable.
---

# CERB Airtable Logger

Turns unstructured freeform time-entry text into correctly structured records in the "Time Tracking"
Airtable table, with a mandatory human preview/confirm gate before anything is written. This is
genuinely judgment work, not arithmetic: dates and hours show up in inconsistent notations, project
mentions are abbreviated or ambiguous, and CERB Section requires reading the actual note text.
`scripts/validate_entries.py` is the one deterministic piece — schema conformance, not judgment — and
runs as a mandatory gate before any write.

**Before starting anything, read `references/rough-data-review-methodology.md`.** It documents concrete
failure modes hit during real backfills and how they were fixed. Data quality gets worse the further
back in time the source goes — expect older backfills to hit these harder, not less.

## Schema

The base layout (tables, field names, field types, the 17 exact `CERB Section` labels) is documented in
`airtable/AIRTABLE-SCHEMA.md` at the repo root. Field **names** are canonical — refer to tables and fields
by name, never by hard-coded IDs.

**Time Tracking** fields this skill writes:

| Field | Type | Notes |
|---|---|---|
| `Date` | date | ISO `YYYY-MM-DD` |
| `Hours` | duration | API value is **integer seconds** (e.g. `7200` = 2h) |
| `Description` | long text | Convention: `"{decimal hours} Hr - {project name} - {note}"` |
| `CERB Section` | multiple select (pick exactly one) | Format `"A8: Design Development"` — labels contain **deliberate typos** (`"Buisness"`, `"Enviromental"`) that must be matched byte-for-byte |
| `Project (linked)` | link to Project Metadata (exactly one) | The only project field the pipeline reads |

**Project Metadata** is the parent table — the master project list this skill resolves and links
against: one row per real project plus one row per internal bucket (the names listed in
`pipeline/settings.json` → `internal_bucket_names`, e.g. VACATION, SICK, STAT, ADMIN, TEAM MEETING,
TRAINING / EVENT), flagged via the `Non-Project / Internal` checkbox. Its primary field `Project Name`
is the canonical name every match resolves to.

**Never hardcode project or choice lists in a prompt or in memory across sessions** — they change as
projects are added. Step 1 below is mandatory every run.

## Step-by-step procedure

### 1. Fetch the live lists, every run
Get the current `CERB Section` choice labels (byte-exact, including the known typos) and the full list
of `Project Name` values (with record IDs) from Project Metadata. If your assistant has an Airtable
connector, use it (a table-schema call and a list-records call); otherwise run
`python -I pipeline/fetch_project_metadata.py` and read `pipeline/project_metadata.json`.

### 2. Segment the input into candidate entries
One entry per line, typically. Drop header/label rows. Merge obvious continuation lines (a note that
wraps without a new date/hours prefix belongs to the entry above it, not a new entry).

For a multi-page OCR'd PDF: segment by **date-range chunks that respect week-header boundaries**, not by
raw page breaks — PDF pages don't align with weeks, and a week header is a more reliable date anchor than
a stray day-label mid-page. See `references/rough-data-review-methodology.md` for why, and for how to
split work across parallel subagents without losing this discipline.

### 3. Parse each entry
Per `references/parsing-conventions.md`: date → ISO, duration → decimal hours → integer seconds, project
mention, note text verbatim.

### 4. Resolve Project against Project Metadata
Matching ladder, in order, against the `Project Name` list fetched in step 1:
1. Exact match against a live project name.
2. Known alias — check the "Project aliases" table in `config/abbreviations.local.md` if it exists,
   else `config/abbreviations.md`.
3. Unique partial/substring match (use the **leading** project mention in the note — see the
   methodology file).
4. Ambiguous (multiple candidates) or no-match — **never guess**. Batch every ambiguous/no-match item
   across the whole input into ONE question block (step 7), not one question per item.

The output of this step is a **Project Metadata record ID**, not a string — that ID is what gets written
in step 11.

**A genuinely new project (no matching Project Metadata row at all) is never auto-created** without
explicit user confirmation first. Once confirmed: create the row with just `Project Name` set (don't
invent Location/Type/Occupancy/GFA/Budget/Storeys — that's the user's job, or
`cerb-submission-builder`'s at submission time), then use its new record ID for the write.

### 5. Suggest CERB Section
From the note text, using `cerb-iap-architecture-internship/references/experience-categories.md`
(category definitions, activity language, and its disambiguation notes for common mix-ups). Show as a
plain suggestion when confident, mark `[?]` when it's a soft guess, and leave blank with no question
asked when the note gives no real signal — "suggest, don't force" is the correct default, not a
shortcut. Internal bucket rows never get a suggested section.

`scripts/suggest_cerb_sections.py` automates this against a staged-entries payload. Use it as a starting
point, not a silent auto-apply: it only assigns when a rule clearly fires. Notes on its configuration:
- Internal buckets come from `internal_bucket_names` in `pipeline/settings.json`.
- Tie-breaking uses the minimum-hours table for your `track` setting (standard or syllabus; both tables
  are built in).
- Its lowest tier (bare phase-tag abbreviations like `SD`/`CA`/`TP`) is **off by default** — enable it
  with `--phase-tags` only if your own notes actually use that tagging habit.

### 6. Build the Description string
`"{decimal hours} Hr - {canonical project name} - {note verbatim}"`, using the resolved canonical
project name and the user's original note text unedited. This skill logs; it doesn't polish prose — that
is `cerb-submission-builder`'s job at submission-build time.

### 7. Preview — mandatory, every run, even for a single line
Show a table: Date | Project | Hours (both h:mm and decimal) | suggested CERB Section | Description |
flags. Follow it with ONE batched question block covering every ambiguity/collision/no-match found
across the entire input. **Nothing is written at this point.**

### 8. Apply the user's answers
Re-preview only if something material changed as a result. A clarifying answer to one question is not,
by itself, consent to write — require an explicit go-ahead separately (see the methodology file's
standing rule).

### 9. Validate
Run `scripts/validate_entries.py` against the staged payload and the live lists fetched in step 1. It
checks date format/range, hours bounds and quarter-hour sanity, byte-exact choice-name matches, and
Description-prefix consistency. **Stop on any error** — do not write a payload the script flags.

### 10. Duplicate check
Query existing records across the input's date range and warn on exact Date+Project+Hours collisions
before writing. Also explicitly check whether the tail end of the input's date range already exists in
Airtable in full — if so, drop that whole sub-range from scope rather than deduping it record-by-record.

### 11. Write via the direct-API script
Every write payload writes `Project (linked)` (the Project Metadata record ID from step 4, as an array of
one).

Default write path: `python -I skills/cerb-airtable-logger/scripts/airtable_write.py --input
<validated-payload.json>`. It reads `AIRTABLE_TOKEN`/`AIRTABLE_BASE_ID` from `pipeline/.env` (point the
`CERB_ENV_FILE` environment variable at a different file to override), defaults to the "Time Tracking"
table (pass `--table` with a table name or ID to change it), chunks internally into the Airtable REST
limit of ≤10 records per call, writes sequentially, and reports one summary line per batch plus a final
count. Pass `--typecast` ONLY for a specific invocation that needs it — never as a standing default. Use
`--dry-run` to sanity-check batch counts before writing. It stops immediately on the first failed chunk
and reports exactly how many records were written before the failure — no blind retry.

**Fallback**: if your assistant has an Airtable connector with a create-records tool, it can be used
instead for the rest of a run rather than debugging the script mid-backfill. Writes made by the script
are reversible through Airtable's own record history.

`scripts/airtable_update.py` is the sibling for PATCHing existing records by ID (e.g. backfilling a CERB
Section suggestion onto already-written rows) — same token, chunking and stop-on-failure behaviour.

**Default cadence: one batch, then stop and let the user confirm before the next one.** Only speed up to
multi-batch runs after the user has verified early batches and explicitly asks — and earn that again each
session.

### 12. Report
Counts written and date range covered. Mention Airtable record history as the undo path (a safety net,
not a substitute for the step-7 preview gate). Offer to save any newly confirmed alias into the "Project
aliases" table of `config/abbreviations.local.md` (create it from `config/abbreviations.md` if missing) —
don't let a resolved ambiguity go unrecorded.

## Known limitations

- **CERB Section inference quality depends entirely on note-text richness.** A one-word note ("meeting")
  gives no real signal and correctly gets no suggestion.
- **Up to 10 records per write call** (the Airtable REST limit) — the scripts chunk automatically.
- **The token needs `data.records:write` scope** for this skill (a read-only token fails with a 403
  `INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND`). See `airtable/AIRTABLE-SCHEMA.md`.
- **Resolves and links the Project Metadata record, but never writes its metadata content.**
  Summary-of-Projects fields (Location, Type, Occupancy, GFA, Budget, Storeys) are filled in by the user
  in Airtable.
- **A brand-new project needs a Project Metadata row before it can be linked** — created (name only) in
  step 4 once the user confirms.
