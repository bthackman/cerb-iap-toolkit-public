# Airtable base: "CERB Log"

The pipeline reads one Airtable base with two tables. Field **names** below are what the code
looks up — keep them exactly as written (including two deliberate typos in the CERB Section labels).

## Fastest setup: copy the template

Open the template base link in the main [README](../README.md#1-get-the-airtable-base) and click
**Copy base**. It contains both tables, the link between them, six internal buckets, and one
`EXAMPLE | Community Library (delete me)` project with four sample time entries you can use to test
the pipeline end to end. Delete the example rows once you've seen a draft generate.

If the link is unavailable, build the base by hand from the tables below (about 10 minutes).

---

## Table 1 — `Project Metadata` (create this one first)

One row per project, plus one row per internal bucket (vacation, admin, …). Holds the
"Summary of Projects" details the CERB form asks for, so you enter them once instead of every period.

| Field | Type | Notes |
|---|---|---|
| `Project Name` | Single line text (**primary field**) | The name printed on the CERB. Spell acronyms out. |
| `Location` | Single line text | `City, Province`. |
| `Project Type` | Single select | New Construction · Addition · Renovation / Alteration · Tenant Improvement · Demolition · Master Planning / Site Development · Other |
| `Occupancy` | Single select | Assembly · Institutional · Industrial · Residential · Commercial · Care and Detention · Mercantile · Business and Personal Services · Transit · N/A |
| `Gross Floor Area` | Single line text | Free text with units, e.g. `45,000 sf`. |
| `Budget` | Single line text | Free text with currency, e.g. `$12M`. |
| `Number of Storeys` | Number (integer) | |
| `Non-Project / Internal` | Checkbox | **Checked = never included in any CERB.** Use for vacation/sick/stat/admin/training buckets, and for real projects you choose to leave out (e.g. work your supervising architect can't sign off). |

Typing `n/a` in Location/GFA/Budget is a valid, complete answer (master plans, hourly work). Only a
**blank** field is treated as missing.

## Table 2 — `Time Tracking`

One row per time entry.

| Field | Type | Notes |
|---|---|---|
| `Date` | Date, ISO format (`YYYY-MM-DD`) — **primary field** | |
| `Hours` | Duration, `h:mm` | Airtable stores this as **seconds**; the pipeline divides by 3600. Log in 15-minute steps. |
| `Description` | Long text | What you actually did. The narrative bullets are written from this. |
| `CERB Section` | Multiple select — pick **exactly one** | 17 options, exact labels below. Rows with no section are left out of the CERB (and reported). |
| `Project (linked)` | Link to `Project Metadata` — link **exactly one** | The only project field the pipeline reads. |

### `CERB Section` options (copy exactly)

```
A1: Programming
A2: Site and Enviromental Analysis
A3: Schematic Design
A4: Engineering Systems Integration
A5: Building Cost Analysis
A6: Code Research
A7: Envelope Detailing
A8: Design Development
A9: Construction Documents
A10: Specifications and Material Research
A11: Document Checking and Coordination
A12: Energy Literacy / Sustainability
B13: Procurement and Contract Award
B14: Construction Phase - Office
B15: Construction Phase - Site
C16: Management of the Project
C17: Buisness / Practice Management
```

`Enviromental` and `Buisness` are misspelled on purpose — they mirror the official form and the
category-suggestion script matches labels byte-for-byte. The CSV adapter only reads the number after
the letter, so if you do fix the spelling, also update the labels in
`skills/cerb-airtable-logger/scripts/suggest_cerb_sections.py`.

## Personal access token

Create one at <https://airtable.com/create/tokens> with:

- Scopes: `data.records:read`, `data.records:write` (write is only needed for the logger skill),
  `schema.bases:read`
- Access: **only** your CERB Log base

Put it in `pipeline/.env` (copy `pipeline/.env.example`). Never commit `.env`.

The base ID is the `app…` part of the base's URL: `https://airtable.com/appXXXXXXXXXXXXXX/…`.
