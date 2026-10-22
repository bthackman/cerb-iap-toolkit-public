# CERB / IAP Toolkit

Turn your Airtable time log into a **draft Canadian Experience Record Book (CERB) submission** for
the Internship in Architecture Program (IAP). It produces the filled official fillable PDF and a
"Project Descriptions — Role of Intern" Word document, written by your AI assistant in the IAP
Manual's own language.

Built to be **set up and run with an AI coding assistant** (Claude Code or GitHub Copilot). You log
hours; the AI handles the scripts, the narrative and the checking; you review and submit.

```
Airtable (Time Tracking + Project Metadata)
        │  run_period.py prepare
        ▼
hours grid per form sheet  ──►  AI writes content.json (narrative)
        │  run_period.py build
        ▼
CERB form PDF  ·  Project Descriptions .docx  ·  progress dashboard
```

## Start here

| You are… | Read |
|---|---|
| The intern using it | **[docs/HOW-TO-USE.md](docs/HOW-TO-USE.md)** (printable PDF: [docs/HOW-TO-USE.pdf](docs/HOW-TO-USE.pdf)) |
| The AI assistant setting it up | **[AGENTS.md](AGENTS.md)** (Claude Code loads it via `CLAUDE.md`; Copilot via `.github/copilot-instructions.md`) |
| Changing the code | [pipeline/README.md](pipeline/README.md) |

Quickest start: clone this repo, open it in Claude Code or VS Code with Copilot, and say
**"Read AGENTS.md and walk me through first-time setup."**

## 1. Get the Airtable base

**Copy the template base:** _link coming soon_. Until then, build it from
[airtable/AIRTABLE-SCHEMA.md](airtable/AIRTABLE-SCHEMA.md) (two tables, about 10 minutes).

## 2. Try it with no setup

```bash
pip install -r requirements.txt
python pipeline/run_period.py prepare --start 2027-01-01 --offline examples/raw_records.json --offline-metadata examples/project_metadata.json
cp examples/content.example.json exports/2027-02-19/content.json
python pipeline/run_period.py build --end 2027-02-19
```

This uses fictional data (3 projects, 72.50 h). The PDF step needs the official form; see below.

## 3. The official form is not included

The fillable CERB PDF and the IAP Manual belong to the Canadian architectural licensing
authorities. Download your own copy and save it as `form/CERB_fillable_form.pdf`. See
[form/README.md](form/README.md).

## What's inside

| Folder | Contents |
|---|---|
| `pipeline/` | `run_period.py` (main entry point), fetch/filter/fill/meta/dashboard scripts, settings |
| `tools/` | Airtable → CSV adapter, multi-sheet splitter, Word document builder |
| `skills/` | Markdown instructions the AI follows: IAP knowledge, submission workflow, reviewer critique, timesheet logger |
| `airtable/` | Base schema |
| `examples/` | Fictional test data |
| `config/` | Your abbreviation glossary and project display names |
| `docs/` | How-to-use guide for interns |

## Features

- Hours come from the data, never typed in: Airtable durations go to a per-category grid, and
  excluded rows are reported, never dropped silently.
- Periods split automatically at 6 months or 1,000 hours.
- Periods with more than 10 projects get continuation sheets (11, 12, 13…), or you can leave out
  small projects.
- Narrative rules aligned to the 17 IAP experience categories, including a confidentiality rule:
  no client or consultant names.
- A built-in "reviewer" pass critiques each draft the way your supervising architect and the
  regulator would.
- Supports both the Standard IAP (3,720 h) and RAIC Syllabus (9,800 h) tracks, plus configurable
  jurisdiction, period rules and internal time buckets.
- Optional: a logger skill that turns old timesheets into Airtable rows, and an Obsidian progress
  note.

## Disclaimer

This is an independent, unofficial tool. It drafts documents; it doesn't submit, sign, or replace
your supervising architect's review. Always check the current IAP Manual and your provincial
regulator's requirements.

MIT licensed. See [LICENSE](LICENSE).
