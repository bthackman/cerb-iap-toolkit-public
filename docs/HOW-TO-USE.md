# CERB Toolkit — How to Use

*A quick guide for interns. Your AI assistant (Claude Code or GitHub Copilot) does the technical
work; this sheet tells you what you do and what to ask it.*

## What you get

Log your hours in Airtable as you work. Every six months (or 1,000 hours), the toolkit produces:

- **The official CERB form, filled in**: your details, the Summary of Projects and the hours grid.
  Every total is calculated by the toolkit.
- **A "Project Descriptions — Role of Intern" Word document**: written by your AI from your own
  time-entry notes, in the IAP Manual's language, with any uncertain items highlighted for you
  to confirm.
- **A progress dashboard** showing your hours against the IAP minimums for each category.

You stay in charge of what gets submitted. You review every draft, your supervisor signs, and
nothing is sent anywhere automatically.

---

## 1. One-time setup (about 1 hour)

Open this folder in VS Code (Copilot) or Claude Code and say:

> **"Read AGENTS.md and walk me through first-time setup."**

Your AI will take you through each step. You'll need:

| ☐ | Item | Where it comes from |
|---|---|---|
| ☐ | Python 3.9 or newer | python.org (your AI can check whether you already have it) |
| ☐ | An Airtable account (free tier is fine) | airtable.com |
| ☐ | A copy of the **CERB Log** template base | Link in the README; click **Copy base** |
| ☐ | An Airtable personal access token | airtable.com/create/tokens (your AI tells you which boxes to tick) |
| ☐ | The official **fillable CERB PDF** | Your provincial association or the RAIC IAP page; save it as `form/CERB_fillable_form.pdf` |
| ☐ | Your details: employer, supervisor, mentor | For `pipeline/identification.json`; your AI helps fill it in |
| ☐ | Your track: Standard IAP (3,720 h) or RAIC Syllabus (9,800 h) | Goes in `pipeline/settings.json` |

The AI first runs a **practice build on made-up data**, so you can see what the output looks like
before connecting your own Airtable.

---

## 2. Every day or week: log your time in Airtable

In the **Time Tracking** table, add one row per task:

| Field | What to enter | Tips |
|---|---|---|
| **Date** | The day | |
| **Hours** | e.g. `2:30` | Use 15-minute steps. |
| **Project (linked)** | Pick the project | Add new projects in **Project Metadata** first. |
| **CERB Section** | Pick **one** of the 17 categories | Unsure? Pick your best guess. The AI flags odd ones later. |
| **Description** | What you actually did | This becomes your CERB narrative, so be specific: *"Code review: exiting and occupant load for level 2 assembly space"* beats *"code stuff"*. |

**Rows without a CERB Section are left off the CERB.** The toolkit lists them so you can fix them.

In the **Project Metadata** table, fill in each project's Location, Type, Occupancy, Floor Area,
Budget and Storeys once. Typing `n/a` is fine (for example, a master plan with no set budget). For
vacation, sick time, admin and similar, tick **Non-Project / Internal**. Tick it on a real project
too if you want that project left out of your CERB, for example work your supervisor can't
sign off.

---

## 3. Every submission period (about 1–2 hours of your time)

Tell your AI:

> **"Prepare my CERB period starting 2027-01-01."** (use your start date)

| Step | Who | What happens |
|---|---|---|
| **1. Prepare** | AI | Pulls your Airtable rows, works out the period, adds up the hours, and tells you how many projects and hours it found, plus anything it left out. |
| **2. Fix gaps** | You | Add missing CERB Sections or project details in Airtable if asked. The AI re-runs. |
| **3. Draft** | AI | Writes the project descriptions and builds the PDF and Word file into `exports/<end-date>/`. |
| **4. Review** | **You** | Open the Word file. **Orange** = the AI's best guess, so confirm or correct it. **Red** = rows the AI thinks aren't architectural experience. Tell the AI your answers in plain words. |
| **5. Clean pass + critique** | AI | Applies your answers, then reviews the draft the way your supervising architect and the regulator would, and tells you what it would push back on. |
| **6. Final check** | **You** | Read both files. Check the PDF's identification page and hours grid. |
| **7. Submit** | **You** | Get signatures and submit as your regulator requires. When it's accepted, tell the AI **"mark this period final."** |

Useful requests:

- *"Leave the Riverside project out of this period."*
- *"Show Project X and Project Y as one project on the CERB."* This changes the CERB only, not Airtable.
- *"Call the project 'Community Library Renovation' on the CERB."*
- *"Which categories am I furthest behind on?"*
- *"I have old timesheets as PDFs. Help me log them into Airtable."*

---

## 4. Good habits

- **Write descriptions for a reviewer, not yourself.** What did *you* do, on what, and why did it
  matter?
- **Don't name clients or consultants** in descriptions you'd be uncomfortable seeing on the CERB.
  The AI uses role terms ("the client") anyway.
- **Spell out acronyms** in `config/abbreviations.md` once, and the AI uses them everywhere.
- **Review every number on the PDF** before signing. The toolkit is careful, but it's your record.
- **Never commit or share** `pipeline/.env` (your Airtable key), `identification.json` or
  `exports/`. They're private by default.

## 5. If something goes wrong

| Symptom | What to do |
|---|---|
| "Form PDF not found" | Save the official form as `form/CERB_fillable_form.pdf` (see `form/README.md`). |
| Airtable error 401/403 | Your token is wrong, has expired, or doesn't include this base. Make a new one. |
| Hours look too low | Check for rows with no CERB Section or no linked project. The prepare summary lists them. |
| PDF fields are blank or in the wrong place | Your form edition may differ. Ask the AI to "check the form's field names against the field map." |
| More than 10 projects | Normal. The toolkit adds a continuation sheet (projects 11, 12…), or you can leave small ones out. |
| Word and PDF disagree | Ask the AI to rebuild. The build warns about this, and the PDF grid is the one to trust. |

*This toolkit drafts. It doesn't submit, sign, or replace your supervisor's review. Always check
your regulator's current requirements and the current IAP Manual.*
