#!/usr/bin/env python3
"""
generate_dashboard.py

Reads exports/*/meta.json and generates exports/dashboard.html -- a
self-contained CERB progress dashboard showing submitted hours tracked against
the total for the `track` in pipeline/settings.json:

  - "standard": the 3,720-hour IAP requirement
  - "syllabus": the 9,800-hour RAIC Syllabus Program total (the 3,720-hour IAP
    experience is logged within it, against higher per-category targets)

See skills/cerb-iap-architecture-internship/references/syllabus-vs-standard.md
for the per-category tables. If CERB_VAULT_DIR is set (env or pipeline/.env),
also writes a "CERB Progress.md" Markdown summary into that folder.

    python generate_dashboard.py
"""

import json
import sys
from datetime import date
from html import escape as html_escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from period_paths import vault_dir  # noqa: E402
from settings import CATEGORY_NAMES, category_targets, exports_dir, get as setting  # noqa: E402

HERE = Path(__file__).parent
EXPORTS_DIR = exports_dir()
TRACK = setting("track")
TRACK_LABEL = "RAIC Syllabus Program" if TRACK == "syllabus" else "IAP (standard track)"
_MINIMUMS, CERB_TOTAL = category_targets(TRACK)

# Optional Markdown-notes folder from $CERB_VAULT_DIR or the CERB_VAULT_DIR key in pipeline/.env
# (see .env.example); unset means the CERB Progress.md note is skipped.
NOTES_DIR = vault_dir()
NOTES_FILE = NOTES_DIR / "CERB Progress.md" if NOTES_DIR else None

# Per-category minimums for the configured track. The flexible/additional-hours pool (760 standard,
# 2,000 syllabus) may be earned in ANY category, so it isn't compared against a single category.
CATEGORY_TARGETS = {str(n): (CATEGORY_NAMES[n], hrs) for n, hrs in sorted(_MINIMUMS.items())}
MANDATORY_TOTAL = sum(hrs for _, hrs in CATEGORY_TARGETS.values())
FLEXIBLE_POOL = CERB_TOTAL - MANDATORY_TOTAL


def aggregate_category_hours(submissions):
    """Sum category_hours across all submissions (draft + final) into cumulative per-category totals.

    Submissions recorded before category-level tracking existed (meta.json without a category_hours
    key) are silently skipped for this purpose -- their total_hours still counts toward the overall
    total elsewhere, but they can't contribute a category breakdown that was never captured. Re-run
    generate_meta.py for old periods (with --workdir if applicable) to backfill category_hours.
    """
    totals = {k: 0.0 for k in CATEGORY_TARGETS}
    for s in submissions:
        for cat_num, hrs in (s.get("category_hours") or {}).items():
            if cat_num in totals:
                totals[cat_num] += hrs
    return {k: round(v, 2) for k, v in totals.items()}


def load_identification():
    """pipeline/identification.json, else the most recent period's work copy (for the name only)."""
    candidates = [HERE / "identification.json"]
    if EXPORTS_DIR.exists():
        candidates += sorted(EXPORTS_DIR.glob("*/work/identification.json"), reverse=True)
    for id_path in candidates:
        if id_path.exists():
            with open(id_path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def scan_submissions():
    if not EXPORTS_DIR.exists():
        return []
    results = []
    for folder in sorted(EXPORTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        meta_path = folder / "meta.json"
        if not meta_path.exists():
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        meta["folder"] = folder.name
        results.append(meta)
    return sorted(results, key=lambda x: x.get("period_to", ""))


def fmt_hrs(h):
    return "{:,.2f}".format(h)


def build_html(submissions, ident):
    final_hrs = sum(s["total_hours"] for s in submissions if s.get("status") == "final")
    draft_hrs = sum(s["total_hours"] for s in submissions if s.get("status") == "draft")
    total_logged = final_hrs + draft_hrs
    remaining_hrs = max(0.0, CERB_TOTAL - total_logged)

    pct_final = final_hrs / CERB_TOTAL * 100
    pct_draft = draft_hrs / CERB_TOTAL * 100
    pct_remaining = remaining_hrs / CERB_TOTAL * 100
    pct_total = total_logged / CERB_TOTAL * 100

    intern_name = " ".join(filter(None, [
        ident.get("intern_first_name", ""),
        ident.get("intern_middle_names", ""),
        ident.get("intern_surname", ""),
    ])).strip() or "Intern"

    today_str = date.today().strftime("%B %d, %Y")

    # Build table rows
    rows = ""
    for s in submissions:
        status = s.get("status", "draft")
        badge = '<span class="badge badge-{}">{}</span>'.format(status, status.upper())
        period_from = s.get("period_from", "")
        period_to = s.get("period_to", "")
        period_str = _format_period(period_from, period_to)
        hrs = fmt_hrs(s.get("total_hours", 0))
        proj = s.get("projects", "—")
        rows += """
            <tr>
                <td class="col-period">{}</td>
                <td class="col-hrs">{} hrs</td>
                <td class="col-proj">{}</td>
                <td class="col-status">{}</td>
            </tr>""".format(period_str, hrs, proj, badge)

    if not rows:
        rows = '<tr><td colspan="4" class="empty-row">No submissions yet — run generate_meta.py after each export.</td></tr>'

    # SVG donut chart
    donut_svg = _build_donut(pct_final, pct_draft, pct_remaining, total_logged)

    # Category breakdown -- sorted by remaining hours descending, so the areas needing the most
    # time surface first (that's the whole point of tracking this).
    cat_hours = aggregate_category_hours(submissions)
    cat_ranked = sorted(
        CATEGORY_TARGETS.items(),
        key=lambda kv: max(0.0, kv[1][1] - cat_hours.get(kv[0], 0.0)),
        reverse=True,
    )
    category_rows = ""
    for cat_num, (cat_name, target) in cat_ranked:
        logged = cat_hours.get(cat_num, 0.0)
        remaining = max(0.0, target - logged)
        pct = min(100.0, logged / target * 100) if target else 0.0
        category_rows += """
            <tr>
                <td class="col-catnum">{}</td>
                <td class="col-catname">{}</td>
                <td class="col-hrs">{} / {} hrs</td>
                <td class="col-catbar"><div class="mini-bar"><div class="mini-bar-fill" style="width:{:.1f}%"></div></div></td>
                <td class="col-hrs">{} remaining</td>
            </tr>""".format(cat_num, cat_name, fmt_hrs(logged), fmt_hrs(target), pct, fmt_hrs(remaining))

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CERB Progress — {intern}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  :root {{
    --c-primary:   #1F4E5F;
    --c-secondary: #2E5C7A;
    --c-final:     #1F4E5F;
    --c-draft:     #C17D00;
    --c-remain:    #D8E2E8;
    --c-bg:        #F0F4F6;
    --c-card:      #FFFFFF;
    --c-border:    #D0D9DE;
    --c-text:      #1A2A32;
    --c-muted:     #5E7380;
    --c-badge-final-bg:  #E8F2F6;
    --c-badge-final-fg:  #1F4E5F;
    --c-badge-draft-bg:  #FFF4E0;
    --c-badge-draft-fg:  #8B5500;
    --radius:      10px;
    --shadow:      0 2px 8px rgba(0,0,0,0.08);
  }}

  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 14px;
    background: var(--c-bg);
    color: var(--c-text);
    min-height: 100vh;
    padding: 0;
  }}

  /* ── Header ── */
  header {{
    background: var(--c-primary);
    color: #fff;
    padding: 18px 32px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }}
  header h1 {{
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 0.02em;
  }}
  header .sub {{
    font-size: 13px;
    opacity: 0.75;
    white-space: nowrap;
  }}

  /* ── Layout ── */
  main {{
    max-width: 960px;
    margin: 0 auto;
    padding: 28px 24px 48px;
    display: grid;
    gap: 24px;
  }}

  /* ── Cards ── */
  .card {{
    background: var(--c-card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    border: 1px solid var(--c-border);
    padding: 24px 28px;
  }}

  .card-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--c-muted);
    margin-bottom: 16px;
  }}

  /* ── Progress block ── */
  .progress-block {{
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 32px;
    align-items: center;
  }}

  .donut-wrap {{
    position: relative;
    width: 160px;
    height: 160px;
    flex-shrink: 0;
  }}
  .donut-wrap svg {{
    width: 160px;
    height: 160px;
  }}
  .donut-label {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    line-height: 1.2;
  }}
  .donut-label .pct {{
    font-size: 26px;
    font-weight: 700;
    color: var(--c-primary);
  }}
  .donut-label .pct-sub {{
    font-size: 11px;
    color: var(--c-muted);
  }}

  .progress-right {{
    display: flex;
    flex-direction: column;
    gap: 20px;
  }}

  /* Stacked bar */
  .stacked-bar {{
    height: 14px;
    border-radius: 7px;
    overflow: hidden;
    background: var(--c-remain);
    display: flex;
  }}
  .bar-seg {{
    height: 100%;
    transition: width 0.3s;
  }}
  .bar-final  {{ background: var(--c-final); }}
  .bar-draft  {{ background: var(--c-draft); }}

  /* Stat chips */
  .stats-row {{
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }}
  .stat-chip {{
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--c-bg);
    border-radius: 8px;
    padding: 10px 14px;
    flex: 1;
    min-width: 120px;
  }}
  .chip-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }}
  .dot-final   {{ background: var(--c-final); }}
  .dot-draft   {{ background: var(--c-draft); }}
  .dot-remain  {{ background: #A0B4BE; }}
  .chip-body {{ line-height: 1.3; }}
  .chip-val {{
    font-size: 16px;
    font-weight: 700;
    color: var(--c-text);
  }}
  .chip-lbl {{
    font-size: 11px;
    color: var(--c-muted);
  }}

  /* ── Table ── */
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead th {{
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--c-muted);
    padding: 0 12px 10px;
    border-bottom: 2px solid var(--c-border);
  }}
  tbody tr {{
    border-bottom: 1px solid var(--c-border);
  }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody td {{
    padding: 12px;
    vertical-align: middle;
  }}
  tbody tr:hover {{ background: #F6FAFB; }}

  .col-period {{ font-weight: 600; color: var(--c-text); }}
  .col-hrs    {{ font-variant-numeric: tabular-nums; color: var(--c-secondary); font-weight: 600; white-space: nowrap; }}
  .col-proj   {{ color: var(--c-muted); }}
  .col-status {{ }}
  .col-catnum  {{ color: var(--c-muted); font-variant-numeric: tabular-nums; width: 24px; }}
  .col-catname {{ font-weight: 600; color: var(--c-text); }}
  .col-catbar  {{ width: 160px; }}

  .mini-bar {{
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    background: var(--c-remain);
  }}
  .mini-bar-fill {{
    height: 100%;
    background: var(--c-primary);
  }}

  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
  }}
  .badge-final {{
    background: var(--c-badge-final-bg);
    color: var(--c-badge-final-fg);
  }}
  .badge-draft {{
    background: var(--c-badge-draft-bg);
    color: var(--c-badge-draft-fg);
  }}

  .empty-row {{
    text-align: center;
    color: var(--c-muted);
    padding: 24px;
    font-style: italic;
  }}

  /* ── Footer ── */
  footer {{
    text-align: center;
    font-size: 11px;
    color: var(--c-muted);
    padding: 0 0 24px;
  }}

  @media (max-width: 640px) {{
    .progress-block {{ grid-template-columns: 1fr; }}
    .donut-wrap {{ margin: 0 auto; }}
  }}
</style>
</head>
<body>

<header>
  <h1>CERB / {track_label} &mdash; Progress Tracker</h1>
  <span class="sub">{intern}{jurisdiction} &nbsp;&bull;&nbsp; Updated {today}</span>
</header>

<main>

  <!-- Progress card -->
  <div class="card">
    <div class="card-title">Hours Logged vs. {total_hrs} hr {track_label} Requirement</div>
    <div class="progress-block">

      <div class="donut-wrap">
        {donut}
        <div class="donut-label">
          <div class="pct">{pct_total:.0f}%</div>
          <div class="pct-sub">complete</div>
        </div>
      </div>

      <div class="progress-right">
        <div>
          <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="font-size:13px; color:var(--c-muted);">{logged_hrs} of {total_hrs} hrs logged</span>
            <span style="font-size:13px; font-weight:700; color:var(--c-primary);">{remaining_hrs} remaining</span>
          </div>
          <div class="stacked-bar">
            <div class="bar-seg bar-final"  style="width:{pct_final:.2f}%"></div>
            <div class="bar-seg bar-draft"  style="width:{pct_draft:.2f}%"></div>
          </div>
        </div>

        <div class="stats-row">
          <div class="stat-chip">
            <div class="chip-dot dot-final"></div>
            <div class="chip-body">
              <div class="chip-val">{final_hrs_fmt} hrs</div>
              <div class="chip-lbl">Confirmed Final</div>
            </div>
          </div>
          <div class="stat-chip">
            <div class="chip-dot dot-draft"></div>
            <div class="chip-body">
              <div class="chip-val">{draft_hrs_fmt} hrs</div>
              <div class="chip-lbl">In Draft</div>
            </div>
          </div>
          <div class="stat-chip">
            <div class="chip-dot dot-remain"></div>
            <div class="chip-body">
              <div class="chip-val">{remaining_hrs} hrs</div>
              <div class="chip-lbl">Remaining</div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- Category breakdown -->
  <div class="card">
    <div class="card-title">Category Breakdown &mdash; {track_label} Minimums (most hours needed first; plus {flex_hrs} flexible hrs in any category)</div>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Category</th>
          <th>Logged / Target</th>
          <th></th>
          <th>Remaining</th>
        </tr>
      </thead>
      <tbody>
        {category_rows}
      </tbody>
    </table>
  </div>

  <!-- Submission history -->
  <div class="card">
    <div class="card-title">Submission History</div>
    <table>
      <thead>
        <tr>
          <th>Period</th>
          <th>Hours</th>
          <th>Projects</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

</main>

<footer>Generated {today} &nbsp;&bull;&nbsp; CERB / {track_label} {total_hrs} hr requirement</footer>

</body>
</html>""".format(
        track_label=TRACK_LABEL,
        jurisdiction=(" &nbsp;&bull;&nbsp; " + html_escape(setting("jurisdiction"))) if setting("jurisdiction") else "",
        flex_hrs=fmt_hrs(FLEXIBLE_POOL),
        intern=html_escape(intern_name),
        today=today_str,
        donut=donut_svg,
        pct_total=pct_total,
        logged_hrs=fmt_hrs(total_logged),
        total_hrs=fmt_hrs(CERB_TOTAL),
        remaining_hrs=fmt_hrs(remaining_hrs),
        pct_final=pct_final,
        pct_draft=pct_draft,
        final_hrs_fmt=fmt_hrs(final_hrs),
        draft_hrs_fmt=fmt_hrs(draft_hrs),
        rows=rows,
        category_rows=category_rows,
    )

    return html


def _format_period(from_date, to_date):
    """e.g. 2027-01-01 → 2027-06-30  →  Jan 1 – Jun 30, 2027"""
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        fy, fm, fd = from_date.split("-")
        ty, tm, td = to_date.split("-")
        from_str = "{} {}".format(months[int(fm)], int(fd))
        to_str = "{} {}, {}".format(months[int(tm)], int(td), ty)
        return "{} – {}".format(from_str, to_str)
    except Exception:
        return "{} – {}".format(from_date, to_date)


def _build_donut(pct_final, pct_draft, pct_remaining, total_logged):
    """SVG donut chart with final (teal) + draft (amber) + remaining (grey) segments."""
    cx, cy, r = 80, 80, 60
    stroke_width = 18
    circumference = 2 * 3.14159265 * r

    def arc(pct, color, offset_pct):
        dash = circumference * pct / 100
        gap = circumference - dash
        offset = circumference * (1 - offset_pct / 100)
        return (
            '<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
            'stroke="{color}" stroke-width="{sw}" '
            'stroke-dasharray="{dash:.2f} {gap:.2f}" '
            'stroke-dashoffset="{offset:.2f}" '
            'stroke-linecap="butt" />'
        ).format(cx=cx, cy=cy, r=r, color=color, sw=stroke_width,
                 dash=dash, gap=gap, offset=offset)

    # Segments drawn back-to-front; offset rotates starting point to top (-25% = 12 o'clock)
    svg = '<svg viewBox="0 0 160 160" xmlns="http://www.w3.org/2000/svg">'
    # Background (remaining)
    svg += arc(100, "#D8E2E8", 0)
    # Draft (stacked after final)
    if pct_draft > 0:
        svg += arc(pct_final + pct_draft, "#C17D00", 0)
    # Final on top
    if pct_final > 0:
        svg += arc(pct_final, "#1F4E5F", 0)
    svg += "</svg>"
    return svg


def _progress_bar(pct_final, pct_draft, width=24):
    """Unicode block progress bar: teal=final, amber=draft, light=remaining."""
    n_final = round(pct_final / 100 * width)
    n_draft = round(pct_draft / 100 * width)
    n_remain = width - n_final - n_draft
    return "█" * n_final + "▒" * n_draft + "░" * max(0, n_remain)


def write_progress_note(submissions, ident):
    if NOTES_DIR is None:
        print("CERB_VAULT_DIR not set (optional) -- skipping the Markdown progress note.")
        return
    if not NOTES_DIR.exists():
        print("Notes folder not found at {} -- skipping the Markdown progress note.".format(NOTES_DIR))
        return

    final_hrs  = sum(s["total_hours"] for s in submissions if s.get("status") == "final")
    draft_hrs  = sum(s["total_hours"] for s in submissions if s.get("status") == "draft")
    total_logged = final_hrs + draft_hrs
    remaining  = max(0.0, CERB_TOTAL - total_logged)

    pct_final  = final_hrs  / CERB_TOTAL * 100
    pct_draft  = draft_hrs  / CERB_TOTAL * 100
    pct_total  = total_logged / CERB_TOTAL * 100

    today_iso  = date.today().isoformat()
    today_str  = date.today().strftime("%B %d, %Y")
    bar        = _progress_bar(pct_final, pct_draft)

    intern_name = " ".join(filter(None, [
        ident.get("intern_first_name", ""),
        ident.get("intern_surname", ""),
    ])).strip() or "Intern"

    # Build submission table rows
    table_rows = ""
    for s in submissions:
        period = _format_period(s.get("period_from", ""), s.get("period_to", ""))
        hrs    = "{:.2f}".format(s.get("total_hours", 0))
        proj   = s.get("projects", "-")
        status = s.get("status", "draft").upper()
        table_rows += "| {} | {} hrs | {} | {} |\n".format(period, hrs, proj, status)

    if not table_rows:
        table_rows = "| *No submissions yet* | | | |\n"

    # Category breakdown -- sorted by remaining hours descending, most-needed areas first.
    cat_hours = aggregate_category_hours(submissions)
    cat_ranked = sorted(
        CATEGORY_TARGETS.items(),
        key=lambda kv: max(0.0, kv[1][1] - cat_hours.get(kv[0], 0.0)),
        reverse=True,
    )
    category_table_rows = ""
    for cat_num, (cat_name, target) in cat_ranked:
        logged = cat_hours.get(cat_num, 0.0)
        remaining_cat = max(0.0, target - logged)
        pct = min(100.0, logged / target * 100) if target else 0.0
        category_table_rows += "| {}. {} | {:.1f} / {:.0f} hrs | {:.0f}% | {:.1f} hrs |\n".format(
            cat_num, cat_name, logged, target, pct, remaining_cat)

    # Callout type by state
    # If anything is final: success; all draft: warning; nothing logged: note
    if final_hrs > 0:
        overview_type = "tip"
    elif draft_hrs > 0:
        overview_type = "warning"
    else:
        overview_type = "note"

    note = """\
---
updated: {today_iso}
cerb_final_hours: {final_hrs:.2f}
cerb_draft_hours: {draft_hrs:.2f}
cerb_total_logged: {total_logged:.2f}
cerb_remaining: {remaining:.2f}
cerb_pct_complete: {pct_total:.1f}
---

# CERB / {track_label} Progress

*{intern_name} — Updated {today_str}*

> [!{overview_type}] {bar}  {pct_total:.1f}% complete — {total_logged_fmt} / {cerb_total_fmt} hrs logged

## Breakdown

| | Hours | % of {cerb_total_fmt} |
|---|---|---|
| Confirmed Final | {final_hrs_fmt} hrs | {pct_final:.1f}% |
| In Draft | {draft_hrs_fmt} hrs | {pct_draft:.1f}% |
| Remaining | {remaining_fmt} hrs | {pct_remain:.1f}% |

*Targets follow the `{track}` track set in pipeline/settings.json. The per-category minimums below
add up to {mandatory_fmt} hrs; the remaining {flex_fmt} hrs are a flexible pool that may be earned in
any category. See the `syllabus-vs-standard.md` skill reference for the source tables.*

## Category Breakdown (most hours needed first)

| Category | Logged / Target | % | Remaining |
|---|---|---|---|
{category_table_rows}
## Submission History

| Period | Hours | Projects | Status |
|--------|-------|----------|--------|
{table_rows}
---
*Auto-generated by `generate_dashboard.py` — do not edit manually.*
""".format(
        track_label=TRACK_LABEL,
        track=TRACK,
        mandatory_fmt=fmt_hrs(MANDATORY_TOTAL),
        flex_fmt=fmt_hrs(FLEXIBLE_POOL),
        today_iso=today_iso,
        today_str=today_str,
        intern_name=intern_name,
        bar=bar,
        overview_type=overview_type,
        pct_total=pct_total,
        total_logged=total_logged,
        total_logged_fmt=fmt_hrs(total_logged),
        cerb_total_fmt=fmt_hrs(CERB_TOTAL),
        final_hrs=final_hrs,
        draft_hrs=draft_hrs,
        remaining=remaining,
        final_hrs_fmt=fmt_hrs(final_hrs),
        draft_hrs_fmt=fmt_hrs(draft_hrs),
        remaining_fmt=fmt_hrs(remaining),
        pct_final=pct_final,
        pct_draft=pct_draft,
        pct_remain=100 - pct_final - pct_draft,
        table_rows=table_rows,
        category_table_rows=category_table_rows,
    )

    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        f.write(note)

    print("Progress note written: {}".format(NOTES_FILE))


def main():
    ident = load_identification()
    submissions = scan_submissions()

    html = build_html(submissions, ident)

    out_path = EXPORTS_DIR / "dashboard.html"
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    final_hrs = sum(s["total_hours"] for s in submissions if s.get("status") == "final")
    draft_hrs = sum(s["total_hours"] for s in submissions if s.get("status") == "draft")
    print("Dashboard written: {}".format(out_path))
    print("  {} submission(s)".format(len(submissions)))
    print("  Final : {:.2f} hrs".format(final_hrs))
    print("  Draft : {:.2f} hrs".format(draft_hrs))
    print("  Remaining: {:.2f} / {:.0f} hrs".format(max(0, CERB_TOTAL - final_hrs - draft_hrs), CERB_TOTAL))

    write_progress_note(submissions, ident)


if __name__ == "__main__":
    main()
