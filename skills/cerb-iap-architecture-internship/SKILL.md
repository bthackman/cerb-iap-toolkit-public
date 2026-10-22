---
name: cerb-iap-architecture-internship
description: Expert knowledge of Canada's Internship in Architecture Program (IAP) and the Canadian Experience Record Book (CERB) — the supervised work-experience program and logbook every architecture intern in Canada must complete before licensure. Use this skill whenever the user asks about IAP, CERB, Intern Architect requirements, ROAC jurisdictions, Supervising Architect or Mentor roles/responsibilities, the 17 architectural experience categories (Programming, Schematic Design, Construction Documents, Construction Administration, Management, etc.) and their required hours, the RAIC Syllabus Program's work-experience hours, writing or reviewing CERB project narratives/entries, CERB submission timing or late submissions, changing employer or mentor mid-internship, or any architecture-intern logbook/registration-process question in Canada — even if they don't say "IAP" or "CERB" by name (e.g. "how many hours do I need as an intern architect," "is this a good description of my project for my logbook," "what counts as construction administration experience"). Always consult this skill before answering such questions from general knowledge, since the hour requirements and category definitions are specific and easy to get wrong from memory.
---

# IAP / CERB Knowledge Skill

This skill packages detailed knowledge of Canada's Internship in Architecture Program (IAP) and the
Canadian Experience Record Book (CERB) — sourced from the official 4th Edition IAP Manual (July 2020,
rev. July 2022) plus a RAIC internal hours-comparison document for the Syllabus Program track.

It is a **reference skill**: load the relevant file(s) below as needed for the question at hand rather
than treating this as a rigid step-by-step procedure. Most questions only need one or two of the
reference files, not all of them.

## When to use which reference file

| If the question is about... | Read |
|---|---|
| The overall IAP process, roles (Supervising Architect / Mentor / ROAC jurisdiction), submission cycle, eligibility of experience, transferring jurisdictions, changing employer | `references/iap-process.md` |
| The 17 experience categories, their hour minimums, what activities belong in which category, disambiguating similar categories | `references/experience-categories.md` |
| Anything specific to the **RAIC Syllabus Program** (the user's `track` setting is `syllabus`, or they ask how syllabus hours differ from standard) | `references/syllabus-vs-standard.md` |
| The physical structure/sections of the CERB form itself, what goes in each field, the 4 employer-comment prompts | `references/cerb-form-structure.md` |
| Which association/jurisdiction to contact for jurisdiction-specific rules | `references/jurisdiction-contacts.md` |
| Writing or generating CERB project entries/bullets from raw notes, what makes an entry strong vs. weak, how to phrase activities | `references/writing-good-entries.md` |

## Important framing to carry into every answer

1. **3,720 hours is the standard minimum**; **9,800 hours is the Syllabus Program total** (which
   contains the same 3,720-hour-equivalent architectural experience, just logged against higher
   per-category targets — see `syllabus-vs-standard.md` for exactly how these relate). Never conflate
   these two numbers or treat them as alternatives to choose between.
2. **Check which track the user is on** — `track` in `pipeline/settings.json` (`"standard"` or
   `"syllabus"`). If syllabus, give the syllabus-track numbers and flag the standard-track numbers
   alongside them ("on the Syllabus track your target is X; on the standard track it'd be Y"). If
   standard, give standard numbers. If the setting is missing or the question is about someone else,
   ask rather than picking one silently.
3. **Hours are necessary but not sufficient.** The manual is explicit that competence, not just logged
   time, is what's being assessed. When helping write or review CERB entries, push for entries that show
   what the intern actually *did and understood* on a project, not just a number of hours in a category.
4. **Jurisdiction-specific rules (Appendix B of the source manual) are not included in this skill** —
   the source copy had this appendix blank. Whenever a rule plausibly varies by province (mentor
   exceptions, ARE vs. ExAC acceptance, late-submission tolerance, part-time pre-approval, recognized
   mentor lists, etc.), say so explicitly rather than guessing, and point to
   `references/jurisdiction-contacts.md` for who to actually contact.
5. **When writing or generating CERB entries, the manual's own "Typical required Intern Activities"
   language is the gold standard voice — not freely invented phrasing, and not even prior real
   submissions as a primary source (those are useful structural references, but the manual's activity
   language is authoritative).** See `references/writing-good-entries.md` for the full bullet-generation
   priority order, including when to ask for clarification vs. proceed with a flagged best guess.
6. **Some procedures have likely digitized since this manual edition.** E.g., Ontario's OAA now runs an
   online CERB portal with digital sign-off rather than the manual's print-and-initial-in-ink
   instructions. If the user references a portal or online system, don't insist on the literal paper
   procedure — note that practice may have moved on and defer to their jurisdiction's current
   instructions.

## Quick numbers for fast answers

- Standard minimum: **3,720 hours**, minimum **1.5 years**, registration application can't precede **2
  years** post-admission regardless of hours.
- Submit CERB every **900–1,000 hours** (~6 months) or at every **change of employment**, within **8
  weeks** of the last log entry.
- Late submission (>12 months since last entry) triggers special review, possible fees/interview.
- Mentor required in every jurisdiction **except Québec**; must meet intern at least once per submission
  cycle.
- Syllabus Program total: **9,800 hours** (2020 standard, current as of this skill's creation — see
  `syllabus-vs-standard.md`).
- Up to **760 hours** of pre-graduation (Recognized Student) experience may credit toward the standard
  3,720-hour total.

## Source documents this skill is built from

- *Internship in Architecture Program (IAP) Manual*, 4th Edition, July 1 2020 (revised July 1 2022) —
  ROAC. Appendix B (jurisdiction-specific requirements) was not populated in the source copy.
- *IAP-Syllabus Hours Comparison*, RAIC internal tracking document, revised 2021-11-25, comparing 2013
  vs. 2020 Syllabus hour standards. Confirmed externally (Athabasca University RAIC Syllabus program
  page, current as of Oct 2025) that the 9,800-hour total and 2020 standard remain current.

If asked about something this skill doesn't cover confidently (e.g., a specific jurisdiction's Appendix
B rule, or a post-2022 manual revision), say so plainly rather than guessing, and suggest checking the
jurisdiction directly or searching for the latest manual edition.
