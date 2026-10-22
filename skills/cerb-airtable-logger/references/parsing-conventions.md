# Parsing Conventions

Rules for turning a raw freeform line/note into the five fields the Airtable write payload needs. Where
your base already holds logged records, treat their conventions as the source of truth, not an idealized
format.

## Date

- Target format: ISO `YYYY-MM-DD`.
- In an OCR'd multi-page timesheet, **trust the week-header date over a stray day-of-week label found
  mid-page** — week headers are typed/structured and reliable; in-page day labels are often OCR noise or
  a leftover artifact from the source template.
- Freeform pastes may give a bare day-of-week ("Mon", "Tuesday") with no date at all if the surrounding
  context (a prior line, a section header) already establishes the week. Resolve from context; don't
  invent a date with no anchor in the input — flag it in the step-7 preview instead.
- Cross a month/year boundary carefully — a timesheet week spanning Dec 30 – Jan 2 has every day share a
  "week" but not a month or year; don't assume the header's stated month applies to every date under it.

## Hours

- Source notations seen in practice: `2Hr`, `2 hr`, `2.0 Hr`, `2hr30`, `2:30`, plain `2`, and quarter-hour
  decimals (`0.25`, `0.75`, `1.25`, `4.75`).
- Normalize to **decimal hours** first (e.g. `2hr30` → `2.5`), then to **integer seconds** for the API
  payload: `seconds = round(decimal_hours * 3600)`.
- Sanity bound: flag (don't silently accept) any single entry above ~8 hours or with a sub-quarter-hour
  fraction (e.g. `2.13`) — both are far more likely to be a parsing error than a real logged value when
  time is logged in 15-minute steps.
- OT/overtime hour mentions on the same line as a regular entry: merge into one entry's total unless the
  source text clearly separates them into distinct project/note pairs — don't silently drop the OT
  portion.

## Project resolution

- See the "Project aliases" table in `config/abbreviations.local.md` (or the `config/abbreviations.md`
  template) and `SKILL.md` step 4 for the full matching ladder.
- A bare abbreviation (e.g. "CL" alone, with no full project prefix) is common in handwritten-style
  notes and should be checked against the alias table before treating it as ambiguous or unmapped.
- Typos recur across entries once introduced — once confirmed as a typo-alias for a given input source,
  apply it consistently for the rest of that same source without re-asking, but still record it in the
  alias table so it's caught instantly next time a different source repeats the same typo.

## Description string

```
{decimal hours} Hr - {canonical project name} - {note verbatim}
```

- Internal bucket rows (VACATION, SICK, STAT, etc.) may omit the trailing `- {note}` entirely if the
  source gives no note text — `"8.0 Hr - VACATION"` is a valid pattern, not a gap to fill in.
- Use the **canonical** (Project Metadata) project name in the Description, not the raw input mention —
  e.g. a raw "CL" resolves to canonical "Community Library" and the Description reads
  "... - Community Library - ...".
- Preserve the note text verbatim, including the user's own grammar/spelling — this skill logs, it does
  not edit prose (that's `cerb-submission-builder`'s job at submission-build time).

## Non-CERB admin time (exclude, don't map)

Some timesheets mix in genuinely non-CERB administrative time codes (e.g. "IT Downtime", office social
events) that have no CERB relevance at all. These should be parsed and reported as explicitly
**skipped** in the step-7 preview (with a reason), not silently dropped and not forced into ADMIN or any
other bucket. Confirm with the user before excluding a new time-code pattern not already seen in a prior
run.
