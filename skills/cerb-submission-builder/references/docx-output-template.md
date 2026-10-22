# Project Descriptions Document — Output Template

This describes the docx structure/styling for the standalone "Project Descriptions" attachment — used
because the official CERB form's "Role of Intern" field doesn't give enough room for real project
narratives. The docx is rendered by `tools/docx-builder/build.py` (python-docx) from a period's
`content.json`.

This is an **attachment to** the CERB form, not a replacement for it — the form's identification,
Summary of Projects, and Summary of Experience grid are filled separately (see `pdf-form-fields.md` and
`scripts/cerb_pdf_field_map.py`). The docx and the filled PDF are a **pair of outputs from the same
run**, and the division of labour is strict: **the PDF is the only place numeric/structured data
appears** (identification, project metadata, hours grid); **the docx is narrative only** (project
bullets, flags, exclusions). See "The hours grid belongs in the PDF only" below.

**Document title: `Project Descriptions — Role of Intern`** — matching the official form's "Role of
Intern" field, which this document stands in for. Set this as `content["title"]` for every period.

## `content.json` shape

Written by the AI to `exports/<end>/content.json`; `build.py` snapshots it next to the docx.

```json
{
  "title": "Project Descriptions — Role of Intern",
  "subtitle": "Attachment to CERB — Experience period YYYY-MM-DD to YYYY-MM-DD",
  "note": "DRAFT — flagged items (orange) and exclusions (red) need review before signing.",
  "projects": [
    {
      "number": 1,
      "name": "Community Library",
      "project_type": "New Construction",
      "occupancy": "Assembly",
      "project_brief": "One line: what the project is and what this period's hours covered.",
      "categories": [
        {
          "number": 3,
          "name": "Schematic Design",
          "hours": 12.5,
          "bullets": [
            "Plain-string bullet.",
            {"text": "Bullet with a sub-list, including but not limited to:",
             "sub_items": ["Site and building plans", "Elevations and sections"]}
          ],
          "flags": ["Soft-ambiguity note for the user to confirm."]
        }
      ]
    }
  ],
  "exclusions": ["\"Project | Category | Hours hrs | 'Note'\" — excluded entirely. Reason."],
  "flags_summary": "Optional one-line summary of open flags."
}
```

- `number` is the project's **global** number — page 1 columns are 1–10, page 2 continues at 11, 12…
  (matching the grid manifest). `build.py` checks every project's per-category `hours` against the
  `grid_N.json` files in `exports/<end>/work/` and warns on any mismatch.
- `name` is the **display name** printed on both the docx and the PDF Summary of Projects (it overrides
  the Airtable name there). Use it for spelled-out abbreviations and display renames.
- `project_brief` is required on every project — it also feeds the Role of Intern synopsis on page 2 of
  the PDF. `build.py` warns when one is missing.
- `flags`, `exclusions`, `flags_summary` are draft-pass markup; empty them for the clean pass.

## Rendered structure

```
[Document title + subtitle line + note]

1.  [Project Name]
    [Project Type]  |  [Occupancy]                          <- italic grey meta line
    Project Brief:                                           <- bold label, every project
    [one-paragraph project description]
    Architectural Experience Description:                    <- bold label, every project

    [#].  [Category Name]  |  [X.X] Hours                   <- bold coloured category heading
    • [bullet]
    • [bullet — "…including but not limited to:"]
       o [sub-item]                                          <- second-level bullet, hollow-circle marker
       o [sub-item]
      FLAGGED — ...                                          <- italic orange flag note, indented

    [#].  [Next Category]  |  [X.X] Hours
    • [bullet]

2.  [Next Project Name]
    ...

─────────────────────────
Excluded from this draft
"[Project] | [Category] | [Hours] hrs | '[Note]'" — excluded entirely. [reason].   <- red italic text
─────────────────────────
```

**Category ordering within a project: ascending CERB category number (1, 2, 3, … 17), never
hours-descending.** `build.py` sorts categories this way regardless of their order in `content.json`.
Only omit a category number the project has zero hours in; never renumber. Projects themselves appear in
global-number order, which is hours-descending (largest project first).

**Project Brief / Architectural Experience Description labels: every project gets both, no
exceptions**, however small the project. Write a real one-line brief — what it is, what phase/scope
this period's hours cover.

**Nested "including but not limited to:" sub-bullets**: when a bullet itemizes several deliverable
types, put them in `sub_items` — rendered as a genuine second-level bullet (hollow circle `o`), indented
further than the first-level bullet, not folded into one long sentence.

## Styling (as implemented in `build.py`)

- Font: Arial, 11pt body.
- Page setup: US Letter, 0.75" margins on all sides.
- Title: bold 16pt. Subtitle: italic 10pt grey `595959`. Note: italic 10pt burnt orange `B23A00`.
- Project heading (`N.  Project Name`): bold 14pt, colour `1F4E5F` (dark blue-grey), with a bottom
  border rule in the same colour.
- Meta line (type | occupancy): italic 10pt grey `595959`; omitted fields are simply left out.
- Project Brief / Architectural Experience Description labels: bold 10pt grey `595959`.
- Category heading (`#.  Category Name  |  X.X Hours`): bold 11pt, colour `2E5C7A` (medium blue) —
  distinct from the project heading colour.
- Bullets: hanging indent, `•` first level, `o` second level.
- **Flags**: italic 10pt, burnt orange `B23A00`, indented, prefixed "FLAGGED —" — soft-ambiguity
  best-guess bullets (see `writing-good-entries.md`, point 8).
- **Exclusions**: italic 10pt red `C00000`, in a separate closing section after a red rule — deliberately
  a different colour from flags so "best guess, please confirm" (orange) and "confirmed ineligible,
  please approve removal" (red) are distinguishable at a glance.
- **Page break before every project except the first** — each project starts on a fresh page; no blank
  leading or trailing page.

After building, open the docx in Word to check the layout, especially after any styling change.

## Two-pass workflow reminder (see writing-good-entries.md for the full rule)

1. **Draft pass**: flags (orange) and exclusions (red) both visible. Deliver this first, always.
2. **Clean pass**: after the user resolves flagged/excluded items, regenerate with that markup removed.
   The clean pass is what goes in front of the Supervising Architect and Mentor — never deliver a
   flagged draft as final.

## The hours grid belongs in the PDF only, not in this document

Don't append the Summary of Experience grid as a table inside the docx. Repeating it is redundant and
creates a second place the same numbers could drift out of sync if either output is regenerated
independently. The numeric grid's only home is the filled PDF, computed once by `build_hours_grid.py`.
If a reviewer needs the hours alongside the narrative, present both files together.

## Metadata display when fields are missing

Don't print "[not provided]" for every missing metadata field on the meta line — it gets cluttered.
Show only the fields that have real values, and summarize outstanding metadata once near the top (see
`writing-good-entries.md`, "Communicating unresolved metadata").
