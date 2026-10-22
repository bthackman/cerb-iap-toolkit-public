# Rough-Data Review Methodology

**Read this before starting any backfill.** This is the reusable review discipline plus concrete
failure modes hit while backfilling several years of timesheets into the base, so they get caught
faster (or avoided) instead of being rediscovered from scratch. Expect older source data to be rougher,
not cleaner.

## CERB Section balance-aware tie-breaking

Before running `scripts/suggest_cerb_sections.py` over a new chunk of backfill data, pull a fresh
`--category-totals` snapshot (hours already logged per CERB Section, summed from the live base) and pass
it in. When an entry is genuinely ambiguous between two categories of similar specificity, prefer
whichever is furthest behind its own required minimum **as a percentage**, not raw hours — category
minimums vary widely, so raw comparison would always favour small-minimum categories even after they're
done. The minimum table used follows the `track` setting in `pipeline/settings.json`. This is a
portfolio-balance nudge for genuine ties only; it never overrides a clearly dominant, more-specific
signal (see the script's docstring for the tier mechanics).

**Refresh cadence: roughly every ~6 months of processed source data, not per entry.** This is a coarse
nudge toward balance, not a live-updating optimizer.

## Review discipline (apply every run)

1. **Fetch the live lists first, every run** (SKILL.md step 1). Never reuse a snapshot from a prior
   session or from this file — projects get added.
2. **Segment by date-range chunks that respect week-header boundaries**, not by raw page breaks. A
   week-header date is a more reliable anchor than a stray in-page day label, especially in OCR'd source
   documents where labels can be misread or duplicated.
3. **Parse each entry against the dominant Description convention** already in your base (see
   `parsing-conventions.md`). Assume rough new data is a degraded version of that same convention, not a
   different one, until proven otherwise.
4. **Batch every ambiguous/no-match project resolution into ONE question block per chunk.** Never ask
   one at a time, and never guess silently.
5. **Duplicate-check against the live base by Date+Project+Hours**, and explicitly check whether the
   *tail end* of the input's date range already exists in Airtable in full before scoping the rest of the
   work — overlap doesn't only happen at odd individual records.

## Failure modes seen in practice — expect them again

### 1. Parallel subagents drifting off their parsing instructions
When parsing is split across parallel subagents, some may stop returning the requested JSON and instead
explore the Airtable base themselves or return prose questions.

**Recovery:** look for any scratch files the agents wrote anyway and read them directly; usually no data
is lost.

**Prevention:** make subagent prompts explicit and blunt — *"Return ONLY the JSON object. Do not explore
the Airtable base. Do not ask questions. Do not explain your reasoning."* Use smaller per-agent date
ranges so a bad output is cheap to redo, and check each returned output's shape immediately.

### 2. A resolution rule discovered mid-parse doesn't propagate to other chunks
An alias/auto-resolve rule confirmed partway through a parse won't be in the prompts of chunks that were
already written or dispatched, so matching entries there stay unresolved for no real reason.

**Prevention:** whenever a new resolution rule (an alias, an auto-resolve, a new-project decision) is
confirmed mid-parse, **re-scan every already-completed chunk for the same pattern**. Treat "confirmed
mid-parse" as retroactive, not "from here on."

### 3. PowerShell UTF-8 mojibake silently corrupting non-ASCII characters
Windows PowerShell 5.1's `Get-Content -Raw | ConvertFrom-Json` misreads UTF-8-without-BOM as
Windows-1252, so "façade" silently becomes "faÃ§ade" — no error, just wrong bytes.

**Fix / prevention:** never pipe `Get-Content`/`Out-File`/`ConvertFrom-Json` for this data in PowerShell
5.1. Use `[System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)` and
`[System.IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::UTF8)`, or do the merge in
Python with `encoding="utf-8"`. Before any live write, grep the assembled payload for the mojibake tell
(`Ã`) as a cheap, mandatory check — absence of an error does not mean absence of corruption.

### 4. Stale copy-pasted week-template date labels
A day header's printed month/day can be flatly wrong — an authoring artifact from copying a prior week's
template row forward without updating the date. Taken literally, it can collide with a real entry
logged elsewhere for that date.

**Detection:** if each page has a trailing week-range summary line, trust it over individual day-header
digits. Scan the whole document for day headers whose implied date is non-monotonic (equal to or before
the previous header's date) — this bug surfaces exactly that way, and a full-document scan catches every
instance in one pass.

**Prevention:** derive each entry's date from `(week start) + weekday-name offset`, not from the
day-header's printed digits — the weekday name tends to be reliable where the numeric date drifts. Run
the non-monotonic scan as a standard first step, before segmenting into entries.

### 5. "Already has records" is not the same as "fully populated"
A year that appears already backfilled (perhaps by an earlier manual effort) may contain stub rows with
only Date + Description filled and Hours/Project/CERB Section blank. Records also exist where Project and
Section are set but **Hours** is silently blank.

**Prevention:** run the duplicate-check across the whole year, not a sample, before assuming a year is
blank or done — and ask the user before reconciling on top of a period entered by a different process.
When auditing a period, query for ANY of Hours / Project (linked) / CERB Section being blank across the
full range; after fixing, re-run the same blank check across the WHOLE range once more, since a record
can look complete on the field originally flagged while still blank on another. Stub rows can often be
repaired by parsing the `"{X} Hr"` prefix back out of the Description.

### 6. Regex lessons from older, rougher data
- **Alternation order matters when one option is a prefix of another.** `(?:Hr|Hrs)` matches `Hr` inside
  `Hrs` and leaves a dangling `s`, producing a garbage entry. List the longer alternative first:
  `(?:Hrs|Hr)`.
- **Apply an hours sanity bound at parse time, not just as a later warning.** A continuation line that
  starts with a number (a percentage like `90% - 100%...`, a drawing/reference number) will otherwise be
  misread as a new entry with an absurd hours value. Reject anything above ~20 hours for one entry.
- **Retroactive-date annotations take more than one shape** — a leading weekday prefix (`Sun - ...`), a
  trailing parenthetical (`+0.5 Hr - Overtime (Wed)`), or a wrapped form (`(OT: 0.5 Hr - ... - Applied to
  Thursday)`). Detect the weekday name wherever it appears and set the date to
  `week_monday + weekday_offset`.
- **A day header can wrap across three physical lines** (`May` / `23` / `Mon 8 Hr - STAT`). Merge
  standalone month + standalone day-number + weekday-starting line back into one line before parsing.
- **Cluster unresolved project mentions by NORMALIZED name before judging a cluster "too small to bother
  with."** One project can fragment into several spellings (e.g. `Northgate`, `Northgate Library`,
  `Northgate Lib.`), each small alone but substantial combined.

### 7. A duplicate write pass after a long pause
If a session is paused, resumed, or compacted partway through a many-batch write, the write can restart
from batch 1 without knowing earlier batches were already committed — producing duplicates, and orphaned
pre-fix versions of entries corrected mid-run.

**Fix:** re-query every live record in the range (Date + Hours + Description), build the same key set
from the authoritative staged payload, and delete live records that don't match a staged entry or that
duplicate a key already kept. Confirm final count and total hours match the staged payload exactly.

**Prevention:** after ANY multi-batch write, do a live count + total-hours check against the staged
payload before calling the write done — don't trust per-batch "OK" responses alone.

### 8. Leading-mention project matching, and generic placeholders
A length-sorted substring matcher picks the wrong project when a note mentions two project names on one
line (e.g. "Riverside Clinic - discussion about Community Library details" matching the longer name).
Under the `"{project} - {note}"` convention the **first/leading** mention is the entry's project. Also
never auto-match a generic placeholder project name (e.g. a bucket literally called "Project") — it
produces false positives against the common word appearing incidentally in note text.

## What to expect getting worse in older data

- More handwritten-style abbreviations and inconsistent hour notation within one document.
- More project names that predate your current Project Metadata list — expect more new-project
  confirmations, and lower alias-table coverage.
- Lower-quality OCR → more date-anchor ambiguity → lean harder on week-header trust and flag more
  liberally rather than guessing.
- More genuinely new non-CERB admin time codes — confirm with the user before excluding anything not
  already listed in `parsing-conventions.md`.

## Standing execution rule

Before writing anything live: (1) full parse → (2) one batched question pass per chunk for ambiguous
items → (3) explicit duplicate/overlap check against live data → (4) validate resolved Project/CERB
Section values against the live lists byte-for-byte (`scripts/validate_entries.py`) → (5) get explicit
go-ahead → (6) write in batches, one batch at a time by default, escalating cadence only on the user's
explicit request for that specific run → (7) live count + hours reconciliation.

## Token scope note

The write scripts need a personal access token with `data.records:write` scope. A read-only token fails
with a 403 `INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND`. Before a large backfill, do a one-record
test-write → verify → delete cycle to confirm field-for-field correctness.
