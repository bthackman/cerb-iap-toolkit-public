# Writing CERB Entries: Voice, Structure, and Bullet Generation Logic

This file governs how to turn raw logged hours + notes into submission-quality CERB project entries.
It is the **generation logic** layer — it assumes `experience-categories.md` (the manual's category
definitions and "Typical required Intern Activities" per category) is already loaded as the voice
source of truth.

## The core principle: the manual's own language is the gold standard

The voice to write in is **the IAP manual's own "Typical required Intern Activities" phrasing per
category** — not a freely invented style, and not even past CERB submissions as a primary source (those
are useful structural examples, but the manual's activity language is authoritative). Well-regarded
CERB entries in practice closely echo this manual language back, lightly adapted to the actual project.
This is deliberate: it makes the reviewer's job of mapping logged activity to the official requirement
trivial, which is exactly what a reviewer assessing "competence demonstrated, not just hours logged"
wants to see.

## Confidentiality: never name real companies

**Never reference a real company name in a CERB entry — not the client, not a consultant firm, not a
tenant, not a contractor.** These documents need to stay generic. Use the generic role term instead:
"the client," "the consultant" (or "the structural/mechanical/electrical consultant" when the
discipline matters to the bullet), "a tenant," "the contractor," "the bidding team," etc. This applies
even to well-known brand names that show up incidentally in a note (e.g. a named tenant in a retail
project) — genericize the role or, if useful, the generic type of business ("a coffee retailer") rather
than the brand.

This is a real, recurring failure mode to actively check for on every draft — project notes are pulled
from raw internal logs that do name real companies, and that detail must not survive into the bullet.

**The company name isn't always obviously a company name — watch for it hiding as a place/area name
too.** A phrase like "Northgate-area site options" reads like a generic sub-area label, but "Northgate"
might actually be the client's name. Any proper noun in a source note that could plausibly be an area,
building, or feature name deserves the same scrutiny as an obvious company name — if it's not clearly a
generic architectural term (site, parcel, block, wing, phase), treat it as a possible real name and ask
rather than assume it's safe to carry through (e.g. rewrite as "a secondary parcel within the master
plan").

**If it's genuinely unclear who a named entity in the source note is (client vs. consultant vs. tenant
vs. something else), ask the user rather than guess** — guessing risks either exposing a company's name
or misattributing the role.

Whether a project's own *name* may appear on the CERB (e.g. a public institution's building) is the
user's call — ask once per project and record the answer as a display name (see "Display renames"
below). Bullets stay generic either way.

## Abbreviations: always spell them out

Raw logs and Airtable project names are full of convenience abbreviations. **A reviewer must never see a
bare abbreviation they can't decode.**

- Keep your own glossary in `config/abbreviations.local.md` (private, gitignored; copy the
  `config/abbreviations.md` template). Read the `.local.md` if it exists, else the template.
- Spell out every acronym everywhere a reviewer reads it — project headings, the Summary of Projects
  table's Project Name field (via content.json `name`), the Role of Intern synopsis, and bullets. First
  mention in a project: full term followed by the abbreviation in brackets, e.g. "Request for
  Information (RFI)"; later mentions in the same project may use the short form.
- Project names are the easy place to miss this — check every place a project name string appears
  before calling a period done, not just the narrative headings.
- **Never guess an expansion.** If an abbreviation isn't in the glossary and isn't a standard industry
  term, ask the user, then offer to add the answer to the glossary.

## More projects than fit on one page

The form's Summary of Projects table and Summary of Experience grid hold 10 project columns per page
(`max_projects_per_page` in `pipeline/settings.json`, cannot exceed 10). `run_period.py prepare` splits
automatically, largest-hours-first, and renumbers page 2+ as 11, 12, 13… per the manual's instruction to
add extra sheets.

When a period overflows one page, `prepare` also lists projects under `thin_project_hours` (default 10
hours). **The user decides** whether to keep them (extra sheet) or drop them from this period's CERB
with `prepare --drop-project "Name"` — a submission-scope decision only; the hours stay logged in
Airtable untouched. Never drop anything on your own, and flag it for a real decision if any overflow
project is substantial.

## Display renames vs. data merges

Three different operations — don't confuse them:

1. **Display rename** (clearer or spelled-out name for the reviewer): change only the project's `name`
   in `content.json`. That name flows into both the docx heading and the PDF Summary of Projects.
   **Never rename the Airtable `Project Name` just for presentation.** Re-apply the same display name
   in every period the project appears, so periods stay consistent.
2. **Presentation-only merge** (two Airtable projects that are one project for CERB purposes — e.g.
   split across two billing codes): use `prepare --merge "Source Name=Target Name"` so the source rows
   are relabelled in that period's CSV *before* the hours grid is computed. Categories get re-summed
   correctly as one project. **Airtable data is never touched** — the split there stays, because it
   exists for a real reason. Re-apply the merge for every period where either project has hours; metadata
   comes from the target project's row (fill gaps from the other only if real, never fabricate).
3. **Genuine data-model merge** (the split was never real — e.g. one project accidentally logged under
   two names): fix it in Airtable by relinking the Time Tracking rows to one Project Metadata row — only
   with the user's explicit OK, and leave the emptied row in place unless the user asks to delete it.

Any merge can change which projects make the top-N page cut — re-check the ranking afterwards. If a
project family's treatment is ambiguous, ask; don't extend one family's rule to another by analogy.

## Project Briefs never reference prior periods

A Project Brief describes **only what's covered in the current period**, standalone — never "a
continuation of this project's earlier scope," never "progressing from [an earlier phase]," no callback
to an earlier submission period at all. The project's name already establishes continuity, and a
different reviewer may read each six-month increment with no context for backward references.

## Bullet generation priority order

For each (Project, Category, Hours, Note Description) input row, generate bullets in this order:

1. **Anchor in the manual.** Look up the category's "Typical required Intern Activities" lines in
   `experience-categories.md`. Identify which activity line(s) most plausibly match what the NOTE
   DESCRIPTION describes.
2. **Reword lightly, don't invent freely.** Take that manual activity line as the bullet's structural
   template and voice, then graft in the specifics from the note: actual deliverable names (e.g. "wall
   sections," "envelope details"), real triggers (RFIs, AHJ deficiency review, client-requested add
   services), consultant types involved, etc. The result should read as past-tense/passive
   professional phrasing — "Assisted in...", "Participated in...", "Worked on...", "Reviewed..." — matching
   the manual's own grammatical pattern for that category.
3. **Add project-specific bullets beyond the template if the note supports it.** If the note describes
   something the manual's stock activities don't fully capture (a specific technical challenge, a
   notable deliverable, a named system or standard), add bullets — but the manual-derived bullet should
   still anchor the entry, not be replaced.
4. **Default to leaning on the manual, even when notes are reasonably detailed.** The manual phrasing
   should generally do most of the work, with the note supplying the project-specific detail.
5. **Vary phrasing slightly across repeated instances** of project-specific bullets so the submission
   doesn't read as copy-pasted, while still anchoring to the same manual activity line. (The reusable
   closing bullets below are the exception — reuse those as-is.)
6. **When a note is genuinely unmappable, stop and ask — don't guess silently.** If a note is too thin,
   vague, or ambiguous to identify which manual activity line(s) it corresponds to, ask the user about
   that specific entry rather than inventing detail. This should be the exception, not the norm.
7. **A row may turn out not to belong in the submission at all — exclude it, don't force-fit it.**
   Clarifying an ambiguous row can reveal that the hours aren't eligible architectural experience (per
   `iap-process.md` §6). If the user confirms a row is non-architectural or otherwise ineligible, drop it
   from the draft entirely (and from the grid via an exclusion file). Flag the exclusion explicitly so it
   isn't silently lost from the user's own record-keeping.
8. **When a note is mappable but only loosely, proceed with a best-guess bullet and flag it.** Don't
   interrupt the generation flow for soft ambiguity. Generate the most plausible bullet and add a flag
   (content.json `flags`) so the user can confirm or correct it during review.

## Reusable closing bullets that closely follow the manual's activity language

For administrative/procedural categories, the same closing bullets can appear verbatim or near-verbatim
on every project that has hours in that category. This supersedes point 5's "vary phrasing" for this
class of bullet. Use them as-is whenever a project has hours in the matching category, and only add
wording if a genuine project-specific nuance needs capturing:

- **#9 Construction Documents** — an opening bullet, used whenever the note reflects a permit/AHJ
  submission: "Assisted in submission of construction documentation to authority having jurisdiction.
  Including completion of AHJ required forms and coordination of schedules for the Architect and
  consultants." Plus a closing set, used on every #9 entry with more than a few hours (small entries can
  skip it and carry one project-specific bullet): "Assisted in coordination of all documents produced by
  the Architect and the consultants." / "Development of technical skills in drafting drawings accuracy,
  completeness, clarity, and understanding by others through work in the preparation of detail drawings."
  / "Development of knowledge of professional responsibilities and liabilities arising from the issuance
  of construction documents." (the last two appear together or not at all).
- **#11 Document Checking and Coordination**: "Assisted in review of [building permit / tender /
  construction] drawings for the Architect and consultants in order to coordinate and improve the
  drawings for [IFC / tender / permit] documentation. Including but not limited to:" with sub-items
  "Reviewing drawings for possible conflicts between disciplines" / "Review of drawings for relevance and
  accuracy of dimensions, notes, abbreviations, and indications of Architect and consultant drawings" /
  "Coordination of changes and drawing updates with consultant teams." Plus a closing bullet: "Checked
  architectural and consultant drawings prepared by others for relevance and accuracy of dimensions,
  notes, abbreviations and indications."
- **#12 Energy Literacy/Sustainability**: "Review and data entry of energy model information for building
  permit and energy use intensity tracking."
- **#14 Construction Phase – Office** (three-bullet closing block, used as a unit): "Assisted in
  evaluating requests for information and preparing responses." / "Assisted in interpreting documents and
  preparing consultant recommendations for issuance as supplemental instructions or changes." /
  "Increased familiarity with the legal responsibilities of the Client, Contractor, and Architect."

The lesson generalizes: for any category with a strong "standing professional-development outcome"
bullet in the manual, default to consistent reuse rather than a fresh paraphrase each time —
consistency with an established, accepted format matters more than lexical variety.

## Structural format per project entry

```
[N]. [Project Name] | [Project Type] | [Occupancy] |
Project Brief: [one-line project description — required on every project entry]
Architectural Experience Description:

[Category #]. [Category Name] | [X.X] Hours
• [Bullet 1 — manual-anchored, project-specific detail grafted in]
• [Bullet 2 if warranted]

[Category #]. [Next Category Name] | [X.X] Hours
• ...
```

**Within a project, categories are always ordered by ascending CERB category number (1, 2, 3, … 17) —
never by hours.** Only skip a category number the project has zero hours in that period; never renumber
or compress the sequence. (`build.py` enforces this order when rendering.) This governs order *within* a
project only — projects themselves appear hours-descending within the period (largest first).

**Every project entry gets a `Project Brief`, no exceptions.** Write one line of real context (what the
project is, what phase/scope this period's hours cover) for every project, however small. The brief also
feeds the Role of Intern synopsis on page 2 of the PDF, so a missing brief leaves that project out of the
synopsis.

**Itemizing deliverable types: use a nested sub-list, not a run-on sentence — but only for generic
document/deliverable TYPES, never for specific named or numbered instances.** When a bullet names
several deliverable *types*, use "…including but not limited to:" followed by a sub-list (content.json
bullet as `{"text": ..., "sub_items": [...]}`):
```
• Worked on the preparation and assembly of IFC documentation including but not limited to:
   o Site and building plans, elevations, wall sections, envelope details, and schedules.
```
**Do not itemize specific record identifiers** — individual RFI topics, addendum/change numbers, named
rooms, specific consultant deliverables pulled from a raw log. The CERB needs to know *that* you were
drafting, coordinating, and issuing — not the paper trail. Generalize into the *type* of activity in one
sentence, e.g. "Prepared and issued contract revision addenda throughout the construction phase,
addressing scope clarifications, code compliance items, and design coordination issues raised by the
contractor and consultant team." The test for a sub-item: could it plausibly appear on a *different*
project's entry in the same category? "Floor plans, elevations, wall sections" — yes. "Addendum 49 (roof
curb)" — no; that belongs in the user's personal record, not the CERB.

**Bullet count is a small, roughly fixed inventory per category — it does not scale with hours.** A
category with 13 hours and the same category with 460 hours both carry roughly 3–7 bullets: mostly the
reusable bullets above, plus one or two project-specific bullets carrying "what was different about this
project." Consolidate evidence into that inventory rather than adding a bullet per week of notes.
- Not every project touches every category — most real projects in a six-month period hit somewhere
  between 3 and 8 of the 17. Don't pad categories with no logged hours.
- Past tense, professional, largely passive/agentless voice ("Assisted in...", "Participated in...",
  "Worked on...") — minimize first-person "I" except for a clearly individual judgment/negotiation moment.

## Two-pass delivery: draft (flagged) → clean (resolved)

Every generated submission goes through two passes, never straight to a final on the first attempt:

1. **Draft pass (always delivered first).** Produce the full document with all flagged bullets
   (point 8) and all excluded rows (point 7) visible inline. The user reviews, resolves ambiguities, and
   confirms or corrects each flagged/excluded item.
2. **Clean pass (only after the user responds).** Regenerate incorporating their corrections, with flag
   and exclusion markup removed for resolved items. Only re-flag if a correction introduces a new
   ambiguity.

Never skip straight to a "clean" output — the user's confirmation is what turns a best guess into
something accurate enough to put in front of a Supervising Architect.

## Visual convention for flags and exclusions in the draft pass

- **Flagged bullets**: the flag note renders in distinguishable styling (italic, burnt orange) directly
  beneath the category it concerns, inline — not in a separate appendix.
- **Excluded rows**: kept **inside the same draft document** in a separate closing section, in **red
  text**, distinct from the flag styling, so the two kinds of "needs your attention" are visually
  distinguishable at a glance.
- Both exist so the Supervising Architect never sees draft-stage markup — they're removed by the clean
  pass.

## Communicating unresolved metadata in the clean pass

If project metadata fields (Location, GFA, Budget, Storeys) remain blank after the user's response
because they chose to leave them for this cycle, don't repeat a per-field "[not provided]" placeholder
on every project. Consolidate all outstanding metadata into a single line near the top of the document
(content.json `note` or `subtitle`, e.g. "Outstanding: Budget/Storeys (Project A), Location/GFA (Project
B) — to be supplied in a future cycle."), so the reviewer is aware of the gap. Remember that a
deliberately entered `n/a` is a complete answer, not a gap.

Business-development/proposal-writing hours can pile up in **Business/Practice Management** (#17). That's
reasonable for RFP responses and fee work, but a large block of hours in one category without
category-appropriate bullets is worth flagging back to the user rather than passing through silently.

## What "weak" entries look like (cautionary pattern, not to emulate)

Entries that are weak typically show one or more of:
- Categories left entirely blank across a multi-month project despite the project plausibly touching
  them (e.g. a renovation with zero Code Research hours)
- A "Notes:" field with no content
- One-line entries for categories the manual treats as substantial (e.g. a single generic sentence for
  Business/Practice Management when its manual activity list spans accounting, contracts, marketing,
  RFPs, and insurance awareness)
- Large hour totals in a category with bullets that don't describe activities matching that category's
  manual definition

Avoid producing output with these characteristics, and flag — not silently accept — input data that
would lead to this pattern (e.g. a category with 500+ hours but only a one-line note to draw from).
