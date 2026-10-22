r"""
CERB Section suggester for cerb-airtable-logger. Optional step 5 helper: given a staged-entries
payload (same shape validate_entries.py consumes), suggests a CERB Section for entries where the
note text clearly points to one category, and leaves everything else blank rather than guess.

Design lessons baked in (keep them when extending the rules):

1. Use a PRIORITY CASCADE (first matching tier wins), not "must be the only matching rule."
   A note legitimately contains words from several categories in passing -- e.g. "design options
   modeled... for client review" contains both a Schematic Design signal (design options) and,
   under a naive keyword-uniqueness check, a false Engineering-Systems signal (the word "review"
   sitting near "electrical" a few words later). A human reader isn't confused by this; the
   cascade isn't either, because it looks for the DOMINANT signal in priority order instead of
   demanding lexical uniqueness across the whole rule set.
2. Watch for the trailing-\b digit trap: a pattern like r"\bcr\s?#?\d\b" silently fails against
   "CR 09" because \d matches only the first digit ("0"), and there's no word boundary between
   "0" and "9" -- so the group's own closing \b never matches. Use \d+ (or no trailing \b at all)
   for any pattern that must match a multi-digit number.
3. When an entry is GENUINELY ambiguous between two categories of similar specificity (e.g. "Drawing
   review with client, and met with specifications to discuss materiality" could plausibly be C16
   Management, A10 Specifications, or A11 Document Coordination), prefer whichever candidate is
   furthest behind ITS OWN required minimum -- as a PERCENTAGE of that minimum, not raw hours,
   since category minimums differ several-fold and raw comparison would always favor
   small-minimum categories even after they're already done. The minimums follow the `track`
   setting in pipeline/settings.json (standard or syllabus). This only kicks in for genuine
   same-tier ties (see TIER below); it never overrides a clearly dominant, more-specific signal.
   Refresh the --category-totals snapshot every ~6 months of processed source data, not after
   every entry -- it's a portfolio-balance nudge for real ties, not a live optimizer.
4. Vocabulary gaps are found by re-reading the classifier's output against the FULL, untruncated
   entry text. Examples already folded in: "DD package/drawing/set" (A8), "estimating" (A5),
   "code comparison"/"limiting distance"/bare "exit"/"parking study" (A6), "elevator"/"steel
   structure" (A4), "canopy"/"wall assembly"/"gutter"/bare "glazing"/"threshold"/"roof
   penetration" (A7 -- the manual's own redirect rule means envelope terms beat even an explicit
   "DD package" mention in the SAME entry), "title block"/"phasing plan"/"partition plan"/
   "demolition plan"/bare "issuance" (A9), "task list" (C16), and bare "markup(s)"/"revision
   cloud(ing)" as weaker Document Checking signals (tier 3). A bare "issu(ed|ance)" pattern once
   produced a false positive on software-access wording ("Teams issuance") -- excluded via a
   negative lookbehind.
5. Tier 4 (bare phase-tag abbreviations SD / CA / TP) is OFF by default. It only makes sense if
   your own notes consistently use those tags to mean Schematic Design / Construction
   Administration / a tender package; enable it with --phase-tags after checking that habit holds
   for the source you're processing.

Usage:
    python suggest_cerb_sections.py --input <staged_entries.json> --record-ids <ids.json>
                                     [--category-totals <totals.json>] [--phase-tags]
                                     [--out suggestions.json]

<staged_entries.json>: the same list-of-entry-objects shape validate_entries.py takes (each has at
    least "project_resolved" and "description" or a raw note field).
<ids.json>: a list of Airtable record ids in the SAME ORDER as staged_entries.json, used to build
    the {id, fields: {"CERB Section": [...]}} update payload for airtable_update.py.
<totals.json> (optional): {"A1: Programming": 40.5, "A9: Construction Documents": 210.0, ...} --
    current total hours already logged per CERB Section, queried from Airtable (sum Time Tracking
    Hours grouped by CERB Section) before starting a new chunk of backfill. Without this file,
    same-tier ties fall back to the lowest-numbered candidate and a warning is printed once per run.

Internal bucket projects (settings internal_bucket_names, e.g. VACATION/STAT/SICK/ADMIN/TEAM
MEETING) never get a suggestion -- matches SKILL.md step 5's "suggest, don't force" rule; a blank
is a normal, expected outcome, not a gap to fill at all costs. Read
`references/experience-categories.md`'s Appendix A activity language (in the
cerb-iap-architecture-internship skill) before touching the CASCADE below -- these patterns are
anchored to that text, not invented.
"""

import argparse
import json
import os
import re
import sys

# Repo settings (pipeline/settings.py); built-in defaults if run outside the repo layout.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "pipeline")))
try:
    from settings import category_targets, internal_bucket_names  # noqa: E402
    NON_WORK_PROJECTS = internal_bucket_names()
    _MINIMUMS_BY_NUMBER, _ = category_targets()
except ImportError:
    NON_WORK_PROJECTS = {"VACATION", "SICK", "STAT", "ADMIN", "TEAM MEETING", "TRAINING / EVENT"}
    _MINIMUMS_BY_NUMBER = {  # standard track, IAP Manual Appendix A
        1: 80, 2: 80, 3: 240, 4: 140, 5: 80, 6: 120, 7: 80, 8: 320, 9: 760, 10: 120,
        11: 100, 12: 80, 13: 120, 14: 200, 15: 200, 16: 120, 17: 120,
    }

# Exact Airtable CERB Section option labels (including the baked-in typos "Enviromental" and
# "Buisness" -- they must match byte-for-byte; see airtable/AIRTABLE-SCHEMA.md).
SECTION_LABELS = [
    "A1: Programming", "A2: Site and Enviromental Analysis", "A3: Schematic Design",
    "A4: Engineering Systems Integration", "A5: Building Cost Analysis", "A6: Code Research",
    "A7: Envelope Detailing", "A8: Design Development", "A9: Construction Documents",
    "A10: Specifications and Material Research", "A11: Document Checking and Coordination",
    "A12: Energy Literacy / Sustainability", "B13: Procurement and Contract Award",
    "B14: Construction Phase - Office", "B15: Construction Phase - Site",
    "C16: Management of the Project", "C17: Buisness / Practice Management",
]

# Minimum required hours per CERB Section label for the configured track.
MINIMUM_HOURS = {
    label: _MINIMUMS_BY_NUMBER[int(re.match(r"^[A-Z](\d+)", label).group(1))] for label in SECTION_LABELS
}

# Priority cascade grouped into TIERS. Within a tier, rules are ordered by convenience only --
# what matters is that a match at a HIGHER tier (lower number) always wins outright over a LOWER
# tier match. A genuine tie (2+ distinct sections matching within the SAME tier, and no match at
# any higher tier) is the only case eligible for the category-balance tiebreak.
CASCADE = [
    # Tier 1: highly specific, rarely ambiguous on their own
    (1, re.compile(r"\b(envelope|party wall|parapet|wall section|wall assembl\w*|cladding|reglet|"
                    r"EIFS|fire.?rated wall assembly|standing seam|flashing|waterproofing|"
                    r"roof (assembly|drain|slope|insulation|modeling|penetration)|curtain wall|canop(y|ies)|"
                    r"glazing (schedule|detail|type)s?|vestibule glazing|building envelope|"
                    r"scupper|clerestory|(roof|wall) curb|threshold|\bsill\b|exterior insulation|"
                    r"gutter|\bglazing\b)\b", re.I), "A7: Envelope Detailing"),
    (1, re.compile(r"\b(life.?safety|egress|\bexit\b|occupan(cy|t) load|fire separation|"
                    r"smoke seal|fire joint|safety code officer|plans examiner|\bSCO\b|"
                    r"code (discussion|review|research|comparison|study)|hydrant coverage|"
                    r"limiting distance|truck turning|parking (study|calculation))\b", re.I),
     "A6: Code Research"),
    (1, re.compile(r"\b(energy model|EUI|AIA ?2030|sustainability|LEED)\b", re.I),
     "A12: Energy Literacy / Sustainability"),
    (1, re.compile(r"\b(addend[ua]m|add[\s\-#]*\d+|tender|\bbid\b|procurement|contract award|"
                    r"pre-qualification of bidders?|post tender)\b", re.I),
     "B13: Procurement and Contract Award"),
    (1, re.compile(r"\b(rfi|shop ?drawing|change order|payment (application|certificate)|"
                    r"punch list|deficienc(y|ies)|\bcr\s?#?[a-z]?\d+|BP (response|resubmission|"
                    r"release|comments?)|contractor change forms?)\b", re.I),
     "B14: Construction Phase - Office"),
    (1, re.compile(r"\b(site visit|site meeting|field report|observation report|"
                    r"substantial completion|deficiency list verification)\b", re.I),
     "B15: Construction Phase - Site"),
    (1, re.compile(r"\b(specifications?|spec sections?|product research|master specs?)\b", re.I),
     "A10: Specifications and Material Research"),
    (1, re.compile(r"\b(redicheck|clash detection|cross-check|qa (review|markup)|"
                    r"checked (drawings|consultant)|IFC coordination)\b", re.I),
     "A11: Document Checking and Coordination"),
    # Tier 2: moderately specific -- only consulted if no tier-1 rule fired
    (2, re.compile(r"\b(structural|mechanical|electrical|elevator)\b.{0,25}\b(coordinat\w*|discussion|"
                    r"review\w*|drawings?|scope)\b|\b(coordinat\w*|discussion|review\w*)\b.{0,25}"
                    r"\b(structural|mechanical|electrical|elevator)\b|"
                    r"consultants?['\s]* drawings? (for )?conflicts?|shaft (wall|update)|"
                    r"\belevator\b|steel (structure|beam|post|box beam)", re.I),
     "A4: Engineering Systems Integration"),
    (2, re.compile(r"\b(schematic design|massing|concept design|design options?|sketches?)\b", re.I),
     "A3: Schematic Design"),
    (2, re.compile(r"\b(cost estimat\w*|quantity takeoff|value engineering|budget analysis|"
                    r"cost analysis|area (and|/) volume|\bestimat\w*)\b", re.I), "A5: Building Cost Analysis"),
    (2, re.compile(r"\b(programming|client requirements|user group)\b", re.I), "A1: Programming"),
    (2, re.compile(r"\b(site analysis|feasibility study|easement|land use|legal lines|"
                    r"property line|survey|topo(graphic)?|site coordinates|site boundary)\b", re.I),
     "A2: Site and Enviromental Analysis"),
    # Tier 3: generic fallback -- broadest language, most prone to legitimate multi-way ties
    (3, re.compile(r"\b(work ?plan|team meeting|project (status|schedule)|quality control|"
                    r"qc review|schedule variance|budget (tracking|control)|post-occupancy|"
                    r"project close-?out|BIM Execution Plan|task list)\b", re.I), "C16: Management of the Project"),
    (3, re.compile(r"\b(rfp|rfq|business development|marketing|fee (proposal|negotiation)|"
                    r"internal budgeting|professional liability insurance)\b", re.I),
     "C17: Buisness / Practice Management"),
    (3, re.compile(r"\b(design development|\bDD (package|drawing|set)|discussion (about|regarding|of) design|"
                    r"model updates?|design (updates?|reconfiguration)|detail(ing|s)? (added|updated)|"
                    r"outline spec)\b", re.I), "A8: Design Development"),
    # Markup(s) alone is a real Document Checking signal (incorporating/checking others' redlines)
    # but weaker/more generic than the tier-1 signals above -- placed here so it doesn't steal an
    # entry that also has a more specific envelope/code/procurement/office signal.
    (3, re.compile(r"\bmark ?ups?\b|revision cloud(ing|ed)?\b", re.I), "A11: Document Checking and Coordination"),
    (3, re.compile(r"\b(construction document|working drawings?|"
                    r"(?<!teams )(?<!teams access )issued?( (for|to))?|(?<!teams )issuance|"
                    r"drawing (set|package)|building (plans?|elevations?|sections?)|"
                    r"stair (plan|section|detail)|interior elevations?|door schedule|"
                    r"room (and )?door numbering|floor plan|(phasing|partition|demolition|demo) plans?|"
                    r"title ?block|DP (model|write.?up|sheets?|submission)|BP (drawings?|submission|"
                    r"resubmitted)|printed|finalized (the )?(set|package|drawings?)|"
                    r"drawings? (updated?|updates?)|CADs?)\b", re.I), "A9: Construction Documents"),
    # Tier 4: bare phase-tag abbreviations -- note-taking-habit-dependent, so OFF unless
    # --phase-tags is given (see docstring lesson 5).
    (4, re.compile(r"\bsd\b", re.I), "A3: Schematic Design"),
    (4, re.compile(r"\btp\d*\b", re.I), "A9: Construction Documents"),
    (4, re.compile(r"\bca\b", re.I), "B14: Construction Phase - Office"),
]

_warned_no_totals = False


def classify(note, project, category_totals=None, phase_tags=False):
    global _warned_no_totals
    if (project or "").strip().upper() in NON_WORK_PROJECTS:
        return None

    matched_by_tier = {}
    for tier, pattern, section in CASCADE:
        if tier == 4 and not phase_tags:
            continue
        if pattern.search(note):
            matched_by_tier.setdefault(tier, set()).add(section)

    if not matched_by_tier:
        return None

    top_tier = min(matched_by_tier)
    candidates = matched_by_tier[top_tier]
    if len(candidates) == 1:
        return next(iter(candidates))

    # Genuine same-tier tie -- break by whichever candidate is furthest behind its own
    # required minimum, as a percentage (not raw hours; see module docstring lesson 3).
    if category_totals is None:
        if not _warned_no_totals:
            print("WARNING: same-tier ties found but no --category-totals given -- "
                  "falling back to first-listed candidate for ties. Pass --category-totals "
                  "to enable balance-aware tie-breaking.")
            _warned_no_totals = True
        # Numeric section order (A3 before A10) -- plain string sort put "A10" first.
        return min(candidates, key=_section_number)

    def pct_complete(section):
        minimum = MINIMUM_HOURS.get(section)
        if not minimum:
            return 1.0  # unknown category -- don't let it win a tie by default
        return category_totals.get(section, 0.0) / minimum

    return min(candidates, key=pct_complete)


def _section_number(section):
    """'A10: Specifications...' -> 10; unparsable labels sort last."""
    m = re.match(r"^[A-Za-z]*(\d{1,2})", section)
    return (int(m.group(1)) if m else 99, section)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Staged entries JSON (validate_entries.py shape)")
    parser.add_argument("--record-ids", required=True, help="JSON list of Airtable record ids, same order as --input")
    parser.add_argument("--category-totals", help="JSON {section: hours_logged_so_far} snapshot for tie-breaking")
    parser.add_argument("--phase-tags", action="store_true",
                        help="Enable tier-4 bare SD/CA/TP phase-tag rules (only if your notes use that habit)")
    parser.add_argument("--out", default="cerb_section_suggestions.json")
    args = parser.parse_args()

    entries = json.load(open(args.input, encoding="utf-8"))
    ids = json.load(open(args.record_ids, encoding="utf-8"))
    if len(entries) != len(ids):
        raise SystemExit(f"--input has {len(entries)} entries but --record-ids has {len(ids)} -- must match 1:1")

    category_totals = None
    if args.category_totals:
        category_totals = json.load(open(args.category_totals, encoding="utf-8"))

    suggestions = []
    counts = {}
    for entry, rid in zip(entries, ids):
        project = entry.get("project_resolved", "")
        note = entry.get("description", "")
        section = classify(note, project, category_totals, args.phase_tags)
        suggestions.append({"id": rid, "section": section})
        if section:
            counts[section] = counts.get(section, 0) + 1

    json.dump(suggestions, open(args.out, "w", encoding="utf-8"), indent=2)

    assigned = sum(1 for s in suggestions if s["section"])
    print(f"Total: {len(suggestions)}  Assigned: {assigned}  Blank: {len(suggestions) - assigned}")
    for sec, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>3}x  {sec}")
    print(f"\nWrote {args.out} -- review before converting to an airtable_update.py payload "
          f"(wrap each non-null suggestion as {{'id': ..., 'fields': {{'CERB Section': [section]}}}}).")


if __name__ == "__main__":
    main()
