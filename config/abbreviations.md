# Abbreviations and project aliases (template)

> **Keep your real entries private.** Copy this file to `config/abbreviations.local.md` (gitignored)
> and fill that in — real project names, client names and internal codes don't belong in a public repo.
> The AI assistant reads `config/abbreviations.local.md` if it exists, otherwise this template.
> The example rows below are fictional; replace them.

## Abbreviations

**Rule: always spell out acronyms everywhere a reviewer reads them** — project headings, Summary of
Projects names (content.json `name`), the Role of Intern synopsis, and bullets. First mention in a
project: the full term followed by the abbreviation in brackets, e.g. "Request for Information (RFI)";
later mentions in that project may use the short form. If an abbreviation isn't listed here and isn't a
standard industry term, the assistant must ask you — never guess — and offer to add the answer here.

| Abbreviation | Spell out as | Notes |
|---|---|---|
| CL | Community Library | Short name used in Airtable project names and notes |
| RC | Riverside Clinic | |
| LT | Lakeview Townhomes | |
| (internal meeting / review codes) | (add your own) | e.g. your office's name for a design review meeting — spell it out in the CERB |

Standard industry terms (RFI, IFC, AHJ, DD, CD, CA…) still get spelled out on first mention.

## Project aliases

Used by the `cerb-airtable-logger` skill's matching ladder (step 4) to resolve the way a project is
written in raw notes/timesheets to its canonical `Project Name` in the Airtable **Project Metadata**
table. Add a row whenever an ambiguous mention is resolved, so it's never asked twice.

| Alias seen in raw notes | Canonical Project Name in Project Metadata | Notes |
|---|---|---|
| CL | Community Library | |
| Comm Lib | Community Library | Typo/short form seen in older timesheets |
| Riverside | Riverside Clinic | Only when no other "Riverside" project exists |
| Lakeview TH | Lakeview Townhomes | |

## Display names (optional)

Projects whose CERB display name differs from the Airtable `Project Name` (spelled-out abbreviations,
clearer names). The display name goes in content.json `name`; the Airtable name is never changed for
presentation.

| Airtable Project Name | CERB display name |
|---|---|
| CL \| Phase 2 | Community Library \| Phase 2 |
