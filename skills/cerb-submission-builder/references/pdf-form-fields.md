# Official CERB PDF Form — Field Mapping (Verified)

This maps the fillable form fields of the official CERB Experience Summary Form PDF, confirmed by
direct field extraction and rect-position cross-checking against the **2020 edition ("2020 CERB Fillable
Form")** — the variant with a real AcroForm. (A variant distributed as "unlocked for printing" has no form
fields at all and cannot be filled by this toolkit.) **This mapping was non-trivial to derive — the
form's internal field names are inconsistent and contain real typos baked into the PDF itself (not
transcription errors). Do not re-derive this from scratch; use this file.** The machine-usable version
is `scripts/cerb_pdf_field_map.py`.

The official form is not bundled with this toolkit — see `form/README.md` for where to get it, where to
save it (`form/CERB_fillable_form.pdf`, or the `form_pdf` setting), and a pypdf one-liner to list its
field names if your edition differs from the one this map was verified against.

Auto-filled scope: **Identification fields, the Role of Intern synopsis (page 2), Summary of Projects,
and the Summary of Experience hours grid** — plus, only when the optional `backlog_cutoff_date` setting
is used, the backlog fields listed under page 5 below. Signatures and declaration dates are never
touched. Full narrative goes in the separate docx attachment (per `docx-output-template.md`).

Total fields in the form: 351, across 5 pages.

## Page 1 — Identification (39 fields) — IN SCOPE

| Section | Field ID(s) | Notes |
|---|---|---|
| Intern | `Surname`, `First Name`, `Middle Names` | |
| Intern address | `Address`, `Suite No`, `City`, `ProvinceStateTerritory`, `Country`, `PostalZip Code`, `Phone Number` | |
| Employer | `Practice Name`, `Address_2`, `Suite No_2`, `City_2`, `Country_2`, `ProvinceStateTerritory_2`, `PostalZip Code_2`, `Phone Number_2`, `Email` | Note the `_2` suffix pattern distinguishing employer address from intern address — same field labels, different underlying IDs |
| Employer detail | `Nature od Employers ctivities` (sic — typo baked into the PDF itself, not a transcription error), `Experience Supervisor`, `Position` | |
| Mentor | `Surname_2`, `First Name_2`, `Res Telephone`, `Name of Practice`, `Bus Telephone` | |
| Experience period | `DayRow1`/`MonthRow1`/`YearRow1` (From), `DayRow2`/`MonthRow2`/`YearRow2` (To) | |
| Full/part time | `Check Box2` = Full-Time Experience, `Check Box3` = Part-Time Experience | **Confirmed visually** against the rendered blank form (Check Box2 is the upper checkbox). Both use `checked_value: "/Yes"`, `unchecked_value: "/Off"`. |
| Association use only | `Received by`, `rec'd Date`, `Reviewed by`, `Reviewed date` | **Leave blank** — filled by the regulator, not the intern |

## Page 3 — Summary of Projects (70 fields) — IN SCOPE

Pattern: 7 fields per project slot, slots 1–10. Field naming is **inconsistent** — slot 1 has no
numeric suffix; slots 2–10 do; AND "Number of Storeys" specifically changes capitalization for slot 1
only. Use this exact lookup, don't infer a single formula:

| Field meaning | Slot 1 | Slot 2 | Slot 3 | ... | Slot 10 |
|---|---|---|---|---|---|
| Project Name | `1 Project Name` | `2 Project Name` | `3 Project Name` | ... | `10 Project Name` |
| Location | `Location` | `Location_2` | `Location_3` | ... | `Location_10` |
| Project Type | `Project Type` | `Project Type_2` | `Project Type_3` | ... | `Project Type_10` |
| Occupancy | `Occupancy` | `Occupancy_2` | `Occupancy_3` | ... | `Occupancy_10` |
| Gross Floor Area | `Gross Floor Area` | `Gross Floor Area_2` | `Gross Floor Area_3` | ... | `Gross Floor Area_10` |
| Budget | `Budget` | `Budget_2` | `Budget_3` | ... | `Budget_10` |
| No. of Storeys | `No of Storeys` (capital S) | `No of storeys` (lowercase s) | `No of storeys_2` | ... | `No of storeys_9` |

**The "No of Storeys" row is the one genuine irregularity**: slot 1 = `No of Storeys`, slot 2 =
`No of storeys` (no `_2` suffix, different capitalization), slot 3 onward = `No of storeys_2` through
`No of storeys_9` (i.e. offset by one from the other fields' `_N` suffix pattern). Build this row's
field name lookup explicitly, not from a single generated pattern — see
`scripts/cerb_pdf_field_map.py`'s `project_field_names(slot)` function for the verified mapping.

## Page 2 — Role of Intern (1 field) — IN SCOPE

`Role of Intern` — a free-text field. `generate_pdf_field_values.py` fills it with the
`role_of_intern_header` setting followed by `(N) Project Name` + that project's `project_brief` from
`content.json`, for the projects on that sheet. Left untouched if no `content.json` is supplied.

## Page 4 — Summary of Experience hours grid (233 fields) — IN SCOPE

Three separate letter-column grids, one per category section, each with its own row-total column and
its own subtotal row. Project columns 1–10 map to letters in sequence within each grid (grid restarts
its lettering for each category section — it does NOT continue A–Z across all 17 rows).

### Category A (rows 1–12, letters A–J)
- Cell field name: `{letter}{row}` — e.g. `A1` = category 1 (Programming) × project column 1 (=
  letter A), `J12` = category 12 (Energy Literacy) × project column 10 (= letter J).
- Letters A,B,C,D,E,F,G,H,I,J = project columns 1,2,3,4,5,6,7,8,9,10 respectively.
- Row total (sum across that category row): `TOTALSRow{row}` for rows 1–12, e.g. `TOTALSRow1` through
  `TOTALSRow12`.
- Subtotal row (Category A overall subtotal, one cell per project column): `{letter}Subtotal` —
  **but note two genuine typos in the PDF itself**: `ESubtoal` (missing second `t`) and `FSubotal`
  (transposed letters), not `ESubtotal`/`FSubotal`. The other 8 follow the expected pattern
  (`ASubtotal`, `BSubtotal`, `CSubtotal`, `DSubtotal`, `GSubtotal`, `HSubtotal`, `ISubtotal`,
  `JSubtotal`).
- Subtotal-row grand total (Category A subtotal, summed across all projects): `TOTALSRow13`.

### Category B (rows 13–15 of the manual's numbering, but grid letters restart at row 1; letters K–T)
- Cell field name: `{letter}{row}` where row is **1, 2, or 3** (NOT 13/14/15 — the grid's internal row
  numbering restarts per section, even though the manual's category numbers are 13/14/15) — e.g. `K1` =
  category 13 (Procurement) × project column 1, `T3` = category 15 (Construction Phase – Site) ×
  project column 10.
- Letters K,L,M,N,O,P,Q,R,S,T = project columns 1–10 respectively.
- Row total: `TOTALSRow14`, `TOTALSRow15`, `TOTALSRow16` for grid rows 1, 2, 3 respectively (i.e.
  offset by +13 from the grid's internal row number — this offset is NOT obvious from the field name
  alone and was confirmed only by cross-checking y-coordinates).
- Subtotal row: `{letter}Subtotal` for K–T, all following the expected pattern (no typos in this
  section) — `KSubtotal` through `TSubtotal`.
- Subtotal-row grand total: `TOTALSRow17`.

### Category C (rows 16–17 of the manual's numbering, grid letters restart again; letters U–DD)
- Cell field name: `{letter}{row}` where row is **1 or 2** — e.g. `U1` = category 16 (Project
  Management) × project column 1, `DD2` = category 17 (Business/Practice Management) × project
  column 10.
- Letters U,V,W,X,Y,Z,AA,BB,CC,DD = project columns 1–10 respectively (note the move to
  double-letter IDs after Z, same convention as spreadsheet column naming).
- Row total: `TOTALSRow1_2` and `TOTALSRow2_2` for grid rows 1, 2 respectively (the `_2` suffix here
  means something completely different from the `_2` suffix on page 3's fields — it's a PDF-internal
  disambiguation against the page-1 `TOTALSRow1`/`TOTALSRow2`-shaped names, not a project-slot
  indicator. Don't confuse this with the page 3 convention.)
- Subtotal row: `{letter}Subtotal` for U–DD, all following the expected pattern — `USubtotal` through
  `DDSubtotal`.
- Subtotal-row grand total: `TOTALSRow3_2`.

### Grand total row (bottom of the whole grid, one cell per project column + overall)
- Per-project-column grand total (sum of that project's hours across all 17 categories):
  `GT1` through `GT10`.
- Overall grand total (sum of everything): `Grand Total`.

### Declaration fields on page 4 (NOT in scope — leave blank)
- `intern declare date`, `Intern declar name` (sic) — these belong to the Intern Declaration signature
  block; out of this skill's scope (signatures happen after human review).

## Page 5 — Comments and Declarations (8 fields) — OUT OF SCOPE except optional backlog auto-fill
Employer comments, Supervising Architect declaration, Mentor declaration — filled by hand after the
Supervising Architect and Mentor have reviewed the docx narrative attachment.

The one exception is the **optional backlog auto-fill** (`backlog_cutoff_date` setting; off when null):
`Question1`–`Question4` (the four Comments by Employer boxes) and `Mentor name` (Mentor Declaration
name), together with page 1's `Surname_2` (Mentor Identification surname), receive `backlog_text` for
periods ending before the cutoff, and are explicitly cleared for periods ending on/after it. With the
setting null, these page-5 fields are never touched. Signature/date fields are never touched.

## Verification status

`Check Box2` = Full-Time Experience, `Check Box3` = Part-Time Experience (confirmed visually against
the rendered blank form), both using `checked_value: "/Yes"` / `unchecked_value: "/Off"`. No remaining
open items for the 2020 edition.

## Build approach

This form has real AcroForm fields, so it's filled by field name, not by coordinates.
`scripts/generate_pdf_field_values.py` builds `field_values_N.json` from the hours grid, the converted
project metadata, identification, and `content.json`, using `scripts/cerb_pdf_field_map.py`; then
`pipeline/fill_fillable_fields.py` writes the filled PDF. `pipeline/run_period.py build` runs both for
every page.
