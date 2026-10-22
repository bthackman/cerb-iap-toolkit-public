# The CERB form (not included)

The pipeline fills the **official fillable CERB form** (the Canadian Experience Record Book
Experience Summary Form). That PDF belongs to the Canadian architectural licensing authorities and
the RAIC, so it is **not** in this repository, and `.gitignore` keeps any PDF in this folder out of
git.

## Get the form

1. Download the current fillable CERB form from your provincial/territorial association's intern
   (IAP) page, or from the RAIC's IAP / Syllabus pages.
2. Save it here, named exactly:

   ```
   form/CERB_fillable_form.pdf
   ```

   To keep it somewhere else, set `form_pdf` in `pipeline/settings.json`, set the `CERB_FORM_PDF`
   environment variable, or pass `--form PATH` to `run_period.py build`.

## Which edition works

The field map in
[`skills/cerb-submission-builder/references/pdf-form-fields.md`](../skills/cerb-submission-builder/references/pdf-form-fields.md)
(and its code version, `skills/cerb-submission-builder/scripts/cerb_pdf_field_map.py`) was verified
against the **2020 edition, "2020 CERB Fillable Form"**: the one with real fillable fields (an
AcroForm, 351 fields over 5 pages).

Some sites also offer an **"unlocked for printing"** variant. It has **no form fields**, so it
won't work. `fill_fillable_fields.py` stops with a message if you point it at a PDF without fields.

## If your edition differs

List the field names in your copy:

```
python -I -c "from pypdf import PdfReader; import sys; f = PdfReader(sys.argv[1]).get_fields() or {}; print(len(f), 'fields'); print('\n'.join(sorted(f)))" form/CERB_fillable_form.pdf
```

Compare the output with `pdf-form-fields.md`. Expect to see names like `Surname`,
`1 Project Name`, `A1`, `ESubtoal` (sic) and `Grand Total`. When `fill_fillable_fields.py` finds
field names that your form doesn't have, it prints a warning listing them. If names changed in
your edition, update `cerb_pdf_field_map.py` and `pdf-form-fields.md` together, then check a
filled copy page by page before you rely on it.
