# RAIC Syllabus Program vs. Standard IAP Track

## How these two relate (important — they are not competing standards)

The RAIC Syllabus Program is an **alternate educational route** to licensure for people who don't hold a
CACB-accredited degree. It combines academic coursework + design studios + work experience into one
program run by the RAIC.

The **3,720-hour IAP/CERB experience requirement is the same baseline for everyone**, syllabus or not.
What's different is that Syllabus students log a **larger total of 9,800 hours** overall — the IAP's
3,720 hours of architectural experience are a *subset* logged within that bigger syllabus total, using
the **same 17-category CERB structure**, just with higher per-category minimums to reflect the deeper
exposure the syllabus track requires before a student is considered ready.

So: same form, same 17 categories, same Supervising Architect/Mentor mechanics, same submission
cadence (~every 900–1,000 hrs / change of employment / 8-week window) — but bigger numbers per
category, and a longer road overall (9,800 hrs vs. 3,720 hrs).

**Syllabus students are still bound by everything in `iap-process.md` and
`experience-categories.md` — this file only layers the syllabus-specific hour differences on top.**

**In this toolkit**, the `track` setting in `pipeline/settings.json` (`"standard"` or `"syllabus"`)
selects which per-category minimum table `pipeline/generate_dashboard.py` tracks progress against and
which table `suggest_cerb_sections.py` uses for its balance-aware tie-breaking.

## Syllabus hour requirements — 2020 standard (current)

Source: RAIC internal tracking document, "IAP-Syllabus Hours Comparison," revised 2021-11-25.
This compares the older 2013 syllabus standard against the 2020 standard. **2020 is the current
standard** (confirmed independently — Athabasca University's RAIC Syllabus program page, current as of
Oct 2025, states the total is 9,800 hours, matching the 2020 column below).

If a more recent revision of this table surfaces, treat it as authoritative over this file — this data
hasn't been independently re-verified against RAIC past that revision, so **verify against current RAIC
Syllabus communications** and flag to the user if anything here seems inconsistent.

| # | Category / Area | 2013 Hours | **2020 Hours (current)** | Change |
|---|---|---|---|---|
| **A: Design and Construction Documents** | | | | |
| 1 | Programming | 210 | 210 | No change |
| 2 | Site and Environmental Analysis | 210 | 210 | No change |
| 3 | Schematic Design | 315 | **630** | +100% |
| 4 | Engineering Systems Integration | 315 | 370 | +17.5% |
| 5 | Building Cost Analysis | 210 | 210 | No change |
| 6 | Code Research | 315 | 315 | No change |
| 7 | Envelope Detailing | 0 | **210** | NEW category |
| 8 | Design Development | 830 | 830 | No change |
| 9 | Construction Documents | 2,865 | **2,015** | −29.7% |
| 10 | Specifications and Material Research | 315 | 315 | No change |
| 11 | Document Checking and Coordination | 210 | 270 | +28.6% |
| 12 | Energy Literacy/Sustainability | 0 | **210** | NEW category |
| | **Subtotal Min. A** | 5,795 | 5,795 | No change (net) |
| | Additional Hours (A) | 1,580 | 0 | Eliminated |
| | **Total Overall A** | 7,375 | 5,795 | −21.4% |
| **B: Construction Administration** | | | | |
| 13 | Procurement and Contract Award | 210 | 315 | +50% |
| 14 | Construction Phase – Office | 315 | 530 | +68.3% |
| 15 | Construction Phase – Site | 315 | 530 | +68.3% |
| | **Subtotal Min. B** | 840 | 1,375 | +63.7% |
| | Additional Hours (B) | 635 | 0 | Eliminated |
| | **Total Overall B** | 1,475 | 1,375 | −6.8% |
| **C: Management** | | | | |
| 16 | Management of the Project | 315 | 315 | No change |
| 17 | Business/Practice Management | 210 | 315 | +50% |
| | **Subtotal Min. C** | 525 | 630 | +20% |
| | Additional Hours (C) | 215 | 0 | Eliminated |
| | **Total Overall C** | 740 | 630 | −14.9% |
| | **Total Min. Mandatory (A+B+C)** | 9,590 | 7,800 | −18.7% |
| | **Additional/flexible hours** | 210 | **2,000** | +852% |
| | **TOTAL OVERALL** | **9,800** | **9,800** | No change |

### Reading this table correctly

- The **grand total stayed flat at 9,800 hours** between 2013 and 2020 — what changed is the *internal
  distribution*. The 2020 standard shifted weight away from rigid per-category minimums (especially
  Construction Documents, which dropped ~850 hours) and toward a large flexible pool (2,000 "additional
  hours" vs. 210 previously) plus two brand-new mandatory categories: **Envelope Detailing** and
  **Energy Literacy/Sustainability** — both of which also appear as named categories in the standard
  (non-syllabus) IAP manual, so this 2020 revision aligned the syllabus category list with the standard
  CERB categories.
- **Schematic Design roughly doubled** (315 → 630) — by far the largest proportional increase in a
  mandatory category.
- **Construction Documents is still the single largest category by far** (2,015 hrs) even after its
  reduction — same pattern as the standard track, where Construction Documents (760 of 3,720 hrs) is
  also the largest single bucket.

## Side-by-side: Standard track vs. Syllabus 2020, per category

Useful whenever Syllabus and standard-track interns compare progress — the *category names* line up,
but the Syllabus numeric targets are roughly **double to triple** the standard ones in most areas.

| Category | Standard min. hrs | Syllabus 2020 min. hrs | Ratio |
|---|---|---|---|
| Programming | 80 | 210 | ~2.6x |
| Site and Environmental Analysis | 80 | 210 | ~2.6x |
| Schematic Design | 240 | 630 | ~2.6x |
| Engineering Systems Integration | 140 | 370 | ~2.6x |
| Building Cost Analysis | 80 | 210 | ~2.6x |
| Code Research | 120 | 315 | ~2.6x |
| Envelope Detailing | 80 | 210 | ~2.6x |
| Design Development | 320 | 830 | ~2.6x |
| Construction Documents | 760 | 2,015 | ~2.65x |
| Specifications and Material Research | 120 | 315 | ~2.6x |
| Document Checking and Coordination | 100 | 270 | ~2.7x |
| Energy Literacy/Sustainability | 80 | 210 | ~2.6x |
| Procurement and Contract Award | 120 | 315 | ~2.6x |
| Construction Phase – Office | 200 | 530 | ~2.65x |
| Construction Phase – Site | 200 | 530 | ~2.65x |
| Management of the Project | 120 | 315 | ~2.6x |
| Business/Practice Management | 120 | 315 | ~2.6x |
| **Mandatory subtotal (A+B+C)** | **2,960** | **7,800** | ~2.6x |
| Flexible/additional hours | 760 | 2,000 | ~2.6x |
| **Grand total** | **3,720** | **9,800** | ~2.6x |

The ratio is remarkably consistent (~2.6x) across almost every category — the 2020 syllabus standard
appears to have been built by scaling the standard IAP category structure up by a near-constant
multiplier, rather than redistributing weight unevenly across categories. The main *exception* to watch
for is "Additional/flexible hours," which scaled up far more (2.6x as a fraction of a much larger pool)
— syllabus students have significantly more flexible-hour room relative to their mandatory minimums than
standard-track interns do.

## Practical implications for Syllabus students

- Always double check **which set of numbers** is being measured against when comparing progress with
  standard-track interns — same category names, different targets.
- Don't assume an online CERB tool, spreadsheet, or jurisdiction portal is pre-loaded with the Syllabus
  2020 numbers — confirm with the RAIC Syllabus office (or the provincial CERB portal) which hour targets
  it actually validates against, especially since the standard CERB form was originally built around
  the 3,720-hour structure.
- The CERB **submission mechanics** (every 900–1,000 hrs / change of employment / 8-week deadline /
  Supervising Architect + Mentor sign-off) are unchanged for syllabus students — it's only the per-category
  target hours that differ, not the process of logging and submitting.
