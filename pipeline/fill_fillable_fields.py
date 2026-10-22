#!/usr/bin/env python3
"""
fill_fillable_fields.py

Fills a PDF's AcroForm fields from a field_values.json produced by
generate_pdf_field_values.py, then writes the result to an output PDF.

Standing rule: when --out isn't given, the output filename is always dated with the
period's end date (from identification.json's period_to_year/month/day) --
CERB_Page1_DRAFT_{end_date}.pdf -- so the file still identifies itself once it's out
of its exports/{end_date}/ folder (e.g. emailed). Multi-page periods' continuation
sheets get a _page{N} suffix (CERB_Page1_DRAFT_{end_date}_page2.pdf) so page 2 never
overwrites page 1; N comes from --page, else a trailing number in the field-values
filename (field_values_page2.json, field_values_2.json). Pass --out explicitly to
choose the exact filename yourself instead.

USAGE:
    python fill_fillable_fields.py <template.pdf> <field_values.json> [--out <output.pdf>] [--page N]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports under `python -I`
from period_paths import export_dir_for, resolve_identification  # noqa: E402


def check_form(template_path):
    """Fail with an actionable message if the form is missing or has no fillable fields."""
    template_path = Path(template_path)
    if not template_path.exists():
        raise SystemExit(
            "CERB form not found: {}\n"
            "The official fillable form is not included in this repository. Download it from "
            "your provincial association or the RAIC IAP page and save it there -- see "
            "form/README.md.".format(template_path))
    fields = PdfReader(str(template_path)).get_fields() or {}
    if not fields:
        raise SystemExit(
            "{} has no fillable form fields. You probably have the 'unlocked for printing' "
            "variant -- use the fillable (AcroForm) edition instead. See form/README.md.".format(template_path))
    return fields


def fill(template_path, field_values, out_path):
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)

    # Build a dict of field_id -> value for fast lookup
    updates = {entry["field_id"]: entry["value"] for entry in field_values}

    # Apply all updates in one pass
    writer.update_page_form_field_values(writer.pages[0], updates, auto_regenerate=False)

    # pypdf's update_page_form_field_values only operates on one page at a time,
    # but AcroForm fields may span multiple pages. Apply to all pages to be safe.
    for page in writer.pages[1:]:
        writer.update_page_form_field_values(page, updates, auto_regenerate=False)

    with open(out_path, "wb") as f:
        writer.write(f)


def _period_end_date(id_path):
    """Reads period_to_year/month/day from identification.json and returns it as
    'YYYY-MM-DD', or None if the file is missing or those fields aren't set."""
    if not id_path.exists():
        return None
    with open(id_path, encoding="utf-8") as f:
        ident = json.load(f)
    y = ident.get("period_to_year", "")
    m = ident.get("period_to_month", "")
    d = ident.get("period_to_day", "")
    if y and m and d:
        return "{}-{}-{}".format(y, m.zfill(2), d.zfill(2))
    return None


def _page_number(field_values_path, explicit_page=None):
    """Page number for the default filename: --page if given, else a trailing number
    on the field-values filename (field_values_page2.json -> 2), else 1."""
    if explicit_page is not None:
        return explicit_page
    m = re.search(r"(?:page|_)(\d{1,2})\.json$", Path(field_values_path).name, re.IGNORECASE)
    return int(m.group(1)) if m else 1


def _export_dir_from_identification(end_date):
    """Derive exports/{end_date}/ given an already-resolved end_date string."""
    if end_date:
        return export_dir_for(end_date)
    return Path.cwd()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("template_pdf", help="Path to the blank/template CERB PDF")
    parser.add_argument("field_values_json", help="Path to field_values.json from generate_pdf_field_values.py")
    parser.add_argument("--out", default=None, help="Path to write the filled PDF (default: exports/{end_date}/CERB_Page1_DRAFT_{end_date}[_pageN].pdf)")
    parser.add_argument("--page", type=int, default=None, help="Multi-page period sheet number for the default filename (default: parsed from the field-values filename, else 1)")
    args = parser.parse_args()

    if args.out is None:
        id_path = resolve_identification(args.field_values_json)
        end_date = _period_end_date(id_path)
        export_dir = _export_dir_from_identification(end_date)
        page = _page_number(args.field_values_json, args.page)
        page_suffix = "_page{}".format(page) if page > 1 else ""
        if end_date:
            filename = "CERB_Page1_DRAFT_{}{}.pdf".format(end_date, page_suffix)
        else:
            print(
                "WARNING: no period_to_year/month/day in {} -- output filename won't "
                "be dated.".format(id_path),
                file=sys.stderr,
            )
            filename = "CERB_Page1_DRAFT{}.pdf".format(page_suffix)
        args.out = str(export_dir / filename)

    form_fields = check_form(args.template_pdf)

    with open(args.field_values_json, encoding="utf-8") as f:
        field_values = json.load(f)

    missing = sorted({e["field_id"] for e in field_values} - set(form_fields))
    if missing:
        print(
            "WARNING: {} field name(s) not found in this form edition (they will stay blank), e.g. {}. "
            "Your form edition may differ from the mapped 2020 edition -- see form/README.md.".format(
                len(missing), ", ".join(missing[:5])),
            file=sys.stderr,
        )

    fill(args.template_pdf, field_values, args.out)

    filled = sum(1 for e in field_values if e["value"] not in ("", "/Off"))
    print("Filled {} fields into {}".format(filled, args.out))


if __name__ == "__main__":
    main()
