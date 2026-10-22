#!/usr/bin/env python3
"""
cerb_pdf_field_map.py

Verified field-name lookups for the official fillable CERB form PDF, 2020 edition (the
"2020 CERB Fillable Form" with real AcroForm fields -- see form/README.md for how to obtain it
and how to list the field names of a different edition).
See references/pdf-form-fields.md for the full derivation and reasoning -- this module is the
machine-usable version of that document. Do not hand-edit field names without re-verifying against
the form; several of these are confirmed typos baked into the PDF itself, not mistakes here.

This module covers the IN-SCOPE fields: page 1 identification, page 2 Role of Intern synopsis,
page 3 Summary of Projects, page 4 Summary of Experience hours grid, plus the optional page-5
backlog fields (see BACKLOG section below). Signatures/declarations are intentionally not mapped.
"""

# ---------------------------------------------------------------------------
# Page 3: Summary of Projects (up to 10 project slots, 7 fields each)
# ---------------------------------------------------------------------------

def project_field_names(slot):
    """
    Returns a dict of {meaning: field_id} for a given project slot (1-10).
    Handles the form's real inconsistencies (slot 1 has no suffix; "No of Storeys"
    capitalization and suffix offset differ from the other fields).
    """
    if not (1 <= slot <= 10):
        raise ValueError(f"slot must be 1-10, got {slot}")

    suffix = "" if slot == 1 else f"_{slot}"

    # "No of Storeys" is the one genuinely irregular field across slots:
    #   slot 1  -> "No of Storeys"   (capital S, no suffix)
    #   slot 2  -> "No of storeys"   (lowercase s, no suffix)
    #   slot 3  -> "No of storeys_2" (lowercase s, suffix offset by -1 vs other fields)
    #   slot N (N>=3) -> "No of storeys_{N-1}"
    if slot == 1:
        storeys_field = "No of Storeys"
    elif slot == 2:
        storeys_field = "No of storeys"
    else:
        storeys_field = f"No of storeys_{slot - 1}"

    return {
        "project_name": f"{slot} Project Name",
        "location": f"Location{suffix}",
        "project_type": f"Project Type{suffix}",
        "occupancy": f"Occupancy{suffix}",
        "gross_floor_area": f"Gross Floor Area{suffix}",
        "budget": f"Budget{suffix}",
        "storeys": storeys_field,
    }


# ---------------------------------------------------------------------------
# Page 4: Summary of Experience hours grid
# ---------------------------------------------------------------------------

# Project column letters per category section -- each section's lettering restarts, it does NOT
# continue continuously A-Z across all 17 category rows.
_LETTERS_CAT_A = list("ABCDEFGHIJ")           # 10 project columns, Category A (rows 1-12)
_LETTERS_CAT_B = list("KLMNOPQRST")           # 10 project columns, Category B (rows 13-15 -> grid rows 1-3)
_LETTERS_CAT_C = ["U", "V", "W", "X", "Y", "Z", "AA", "BB", "CC", "DD"]  # Category C (rows 16-17 -> grid rows 1-2)

# Confirmed typos baked into the PDF itself for Category A's subtotal row -- do not "fix" these,
# they must match the actual form field names exactly or filling will silently fail.
_CAT_A_SUBTOTAL_TYPOS = {"E": "ESubtoal", "F": "FSubotal"}

# Category number (per the manual's 1-17 numbering) -> (letters list, grid-internal row number,
# row-total field name, subtotal field name template, subtotal-row-total field name)
_CATEGORY_GRID_INFO = {
    1:  (_LETTERS_CAT_A, 1,  "TOTALSRow1"),
    2:  (_LETTERS_CAT_A, 2,  "TOTALSRow2"),
    3:  (_LETTERS_CAT_A, 3,  "TOTALSRow3"),
    4:  (_LETTERS_CAT_A, 4,  "TOTALSRow4"),
    5:  (_LETTERS_CAT_A, 5,  "TOTALSRow5"),
    6:  (_LETTERS_CAT_A, 6,  "TOTALSRow6"),
    7:  (_LETTERS_CAT_A, 7,  "TOTALSRow7"),
    8:  (_LETTERS_CAT_A, 8,  "TOTALSRow8"),
    9:  (_LETTERS_CAT_A, 9,  "TOTALSRow9"),
    10: (_LETTERS_CAT_A, 10, "TOTALSRow10"),
    11: (_LETTERS_CAT_A, 11, "TOTALSRow11"),
    12: (_LETTERS_CAT_A, 12, "TOTALSRow12"),
    13: (_LETTERS_CAT_B, 1,  "TOTALSRow14"),   # NB: +13 offset vs grid-internal row, not +12
    14: (_LETTERS_CAT_B, 2,  "TOTALSRow15"),
    15: (_LETTERS_CAT_B, 3,  "TOTALSRow16"),
    16: (_LETTERS_CAT_C, 1,  "TOTALSRow1_2"),  # NB: page-4-internal "_2" disambiguator, unrelated
    17: (_LETTERS_CAT_C, 2,  "TOTALSRow2_2"),  #     to page 3's per-project-slot "_2" convention
}

_SECTION_FOR_CATEGORY = {**{n: "A" for n in range(1, 13)}, **{n: "B" for n in range(13, 16)}, **{n: "C" for n in (16, 17)}}

# Subtotal-row overall total field, per section
_SECTION_SUBTOTAL_GRAND_FIELD = {"A": "TOTALSRow13", "B": "TOTALSRow17", "C": "TOTALSRow3_2"}


def hours_cell_field_name(category_number, project_column):
    """
    Returns the field_id for the hours cell at (category_number 1-17, project_column 1-10).
    """
    if category_number not in _CATEGORY_GRID_INFO:
        raise ValueError(f"category_number must be 1-17, got {category_number}")
    if not (1 <= project_column <= 10):
        raise ValueError(f"project_column must be 1-10, got {project_column}")

    letters, grid_row, _ = _CATEGORY_GRID_INFO[category_number]
    letter = letters[project_column - 1]
    return f"{letter}{grid_row}"


def category_row_total_field_name(category_number):
    """Returns the field_id for a category row's TOTALS cell (sum across all projects for that row)."""
    if category_number not in _CATEGORY_GRID_INFO:
        raise ValueError(f"category_number must be 1-17, got {category_number}")
    return _CATEGORY_GRID_INFO[category_number][2]


def subtotal_cell_field_name(category_number, project_column):
    """
    Returns the field_id for a section's Subtotal row, for a given project column, given any
    category number that falls in that section (the subtotal row is shared across the section's
    categories, so any valid category_number in that section resolves to the same letters).
    Applies the two confirmed typo field names for Category A's E/F columns.
    """
    if category_number not in _CATEGORY_GRID_INFO:
        raise ValueError(f"category_number must be 1-17, got {category_number}")
    if not (1 <= project_column <= 10):
        raise ValueError(f"project_column must be 1-10, got {project_column}")

    letters, _, _ = _CATEGORY_GRID_INFO[category_number]
    letter = letters[project_column - 1]
    if letter in _CAT_A_SUBTOTAL_TYPOS:
        return _CAT_A_SUBTOTAL_TYPOS[letter]
    return f"{letter}Subtotal"


def section_subtotal_grand_total_field_name(category_number):
    """Returns the field_id for a section's overall subtotal total (e.g. TOTALSRow13 for section A)."""
    section = _SECTION_FOR_CATEGORY[category_number]
    return _SECTION_SUBTOTAL_GRAND_FIELD[section]


def project_grand_total_field_name(project_column):
    """Returns the field_id for a project's grand total across all 17 categories (GT1-GT10)."""
    if not (1 <= project_column <= 10):
        raise ValueError(f"project_column must be 1-10, got {project_column}")
    return f"GT{project_column}"


OVERALL_GRAND_TOTAL_FIELD = "Grand Total"


# ---------------------------------------------------------------------------
# Page 1: Identification fields (flat lookup, no generation needed)
# ---------------------------------------------------------------------------

IDENTIFICATION_FIELDS = {
    "intern_surname": "Surname",
    "intern_first_name": "First Name",
    "intern_middle_names": "Middle Names",
    "intern_address": "Address",
    "intern_suite_no": "Suite No",
    "intern_city": "City",
    "intern_province_state_territory": "ProvinceStateTerritory",
    "intern_country": "Country",
    "intern_postal_zip": "PostalZip Code",
    "intern_phone": "Phone Number",
    "employer_practice_name": "Practice Name",
    "employer_address": "Address_2",
    "employer_suite_no": "Suite No_2",
    "employer_city": "City_2",
    "employer_country": "Country_2",
    "employer_province_state_territory": "ProvinceStateTerritory_2",
    "employer_postal_zip": "PostalZip Code_2",
    "employer_phone": "Phone Number_2",
    "employer_email": "Email",
    "employer_nature_of_activities": "Nature od Employers ctivities",  # sic -- real PDF typo
    "experience_supervisor": "Experience Supervisor",
    "experience_supervisor_position": "Position",
    "mentor_surname": "Surname_2",
    "mentor_first_name": "First Name_2",
    "mentor_res_telephone": "Res Telephone",
    "mentor_practice_name": "Name of Practice",
    "mentor_bus_telephone": "Bus Telephone",
    "period_from_day": "DayRow1",
    "period_from_month": "MonthRow1",
    "period_from_year": "YearRow1",
    "period_to_day": "DayRow2",
    "period_to_month": "MonthRow2",
    "period_to_year": "YearRow2",
}

# Checkboxes -- confirmed visually against the rendered blank form (see pdf-form-fields.md)
FULL_TIME_CHECKBOX_FIELD = "Check Box2"
PART_TIME_CHECKBOX_FIELD = "Check Box3"
CHECKBOX_CHECKED_VALUE = "/Yes"
CHECKBOX_UNCHECKED_VALUE = "/Off"

# Association-use-only fields -- never fill these, they belong to the regulator
ASSOCIATION_USE_ONLY_FIELDS = ["Received by", "rec'd Date", "Reviewed by", "Reviewed date"]

# ---------------------------------------------------------------------------
# Page 2: Role of Intern / "Project(s):" narrative field
# ---------------------------------------------------------------------------

# Verified against the 2020 edition of the fillable form. generate_pdf_field_values.py fills it
# from content.json's per-project project_brief text (header line from settings
# role_of_intern_header, then "(N) <name>\n<brief>" per project) when --content is given.
ROLE_OF_INTERN_FIELD = "Role of Intern"

# ---------------------------------------------------------------------------
# BACKLOG: optional backlog-period fields (page 1 Mentor Identification, page 5 Comments/Mentor
# Declaration)
# ---------------------------------------------------------------------------

# Verified against the 2020 edition. Only used when settings backlog_cutoff_date is set: periods
# ending before that date get settings backlog_text written into these spots (plus Mentor
# Identification's surname, already mapped above as "mentor_surname" -> "Surname_2"); later periods
# get them explicitly cleared. With backlog_cutoff_date = null they are never touched.
COMMENTS_FIELDS = ["Question1", "Question2", "Question3", "Question4"]
MENTOR_DECLARATION_NAME_FIELD = "Mentor name"

# Everything else on page 5 (Super Name, super date, Mentor date, Reviewed by/date) is never touched
# in either direction.
OUT_OF_SCOPE_PAGE_5_FIELDS_NOTE = (
    "Page 5 (Comments and Declarations) is out of scope except Question1-4 and 'Mentor name' "
    "(optional backlog auto-fill, see COMMENTS_FIELDS/MENTOR_DECLARATION_NAME_FIELD above). Page 4 "
    "also has two out-of-scope fields: 'intern declare date' and \"Intern declar name\" (sic) -- the "
    "Intern Declaration signature block."
)
