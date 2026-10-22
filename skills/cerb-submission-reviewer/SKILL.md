---
name: cerb-submission-reviewer
description: Simulates the critical read a CERB project-descriptions draft will actually get before submission -- first from the intern's own Supervising Architect (who signs the Comments and Declarations), then from the reviewer at the intern's licensing jurisdiction (the `jurisdiction` setting in pipeline/settings.json, e.g. the Alberta Association of Architects) who evaluates it before issuing a Periodic Assessment Form. Runs automatically as the final step of cerb-submission-builder's clean pass. Can also be invoked standalone whenever asked to "review this like my supervisor/reviewer would," "sanity check this submission," or similar, against any existing project-descriptions draft. Depends on cerb-iap-architecture-internship for the real IAP manual standards this review is grounded in -- load iap-process.md and cerb-form-structure.md alongside this one, not just this skill's own references.
---

# CERB Submission Reviewer

A **critique layer**, not a data-transformation step: takes a finished project-descriptions draft (the
output of `cerb-submission-builder`) and reads it the way a skeptical, experienced reviewer actually
would — not the way the tool that wrote it would. This exists because the tool that generates a
submission is a poor judge of whether that submission would actually survive real review; a second,
independently-grounded pass catches what generation-time optimism misses.

**Runs automatically as step 9 of `cerb-submission-builder`'s clean pass** — every clean-pass draft
gets this review before being presented as finished. Can also run standalone against any existing draft
on request.

**Jurisdiction**: read `jurisdiction` from `pipeline/settings.json` (e.g. "Alberta Association of
Architects (AAA)") and use it wherever this skill says "the jurisdiction." If it isn't set, ask the
user which association they're registered with.

## Before starting: load the real standard, don't invent one

Read (or confirm already loaded in context):
- `cerb-iap-architecture-internship/references/iap-process.md` §7 ("Fulfilment standard") — the actual
  "competence, not hours" and "variety" requirements this review enforces.
- `cerb-iap-architecture-internship/references/cerb-form-structure.md` — the four employer comment
  prompts the Supervising Architect must answer, and the Summary of Projects / Summary of Experience
  structural requirements.
- `cerb-iap-architecture-internship/references/experience-categories.md` — category minimums and the
  manual's own "Typical required Intern Activities" language, used to check bullets actually match their
  assigned category.
- `references/reviewer-persona.md` (this skill) — the persona voice and the concrete review checklist.
  This is the operative procedure; don't reconstruct it from memory across sessions.

Never invent a review criterion that isn't traceable to one of these source files or to general
professional judgment a reviewing architect would plausibly apply. The goal is to simulate the *real*
review this submission will actually face, not an imagined stricter or looser one.

## Procedure

1. **Take the draft as input.** A completed clean-pass project-descriptions document, plus — if
   available — the hours grid it's paired with, for the consistency check in step 4 of the checklist.
2. **Adopt the persona** from `references/reviewer-persona.md`: a senior architect registered with the
   configured jurisdiction, reading in two capacities in sequence — first as the intern's own
   Supervising Architect, then as the jurisdiction reviewer.
3. **Work through the checklist** in `references/reviewer-persona.md` systematically, project by project
   and category by category. Don't skim, and don't produce generic feedback — every finding names the
   specific project, category, and bullet or hour figure it concerns.
4. **Cross-check hours consistency** whenever a hours grid is available. A mismatch between the
   narrative's stated hours and the grid is always a real, reportable finding — never skip this check
   because it seems mechanical.
5. **Draft the four employer comment prompts** as the Supervising Architect would actually write them
   given this specific draft (see `cerb-form-structure.md` for the prompts). If the draft doesn't
   support a credible answer to one, say so explicitly rather than writing a generic placeholder answer.
6. **Write the review memo** per the structure in `references/reviewer-persona.md`: overall impression,
   per-project findings, the four prompt answers, and a verdict.
7. **Give a real verdict** — one of *would sign as-is*, *needs revision before signing*, or *needs
   revision before jurisdiction submission*. Don't default to the softest verdict to be agreeable; if
   the draft has genuine gaps, say the submission isn't ready and say exactly what would fix it.
8. **Deliver alongside the draft, not instead of it.** This review supplements the clean-pass draft — it
   never rewrites bullets, recomputes hours, or edits the Airtable base. If its verdict calls for
   changes, those changes go back through `cerb-submission-builder`'s own revision flow, not applied
   silently here.

## What this skill is not

- **Not a second data-transformation pass.** It never touches the narrative, the hours grid, or the live
  Airtable base — pure critique, delivered as a separate document alongside the draft.
- **Not a rubber stamp.** A review that finds nothing wrong on every single run is a sign the persona
  isn't being applied critically enough, not a sign the toolkit produces a flawless draft every time —
  stay skeptical of the tendency to be agreeable with your own prior output.
- **Not a substitute for the real Supervising Architect and jurisdiction review.** It's a rehearsal, so
  fewer surprises happen at the real signature and submission stage — not a replacement for either.
