
# Watchlist PDF → CSV Extractor

A small, reliable utility to convert MAS alert-list PDFs into a CSV that matches your **Fave Watchlist** format and business rules. It is designed to be **exact-match safe**: if any extracted value does not match the PDF text verbatim, the script aborts and does not write output.

---

## 1) Project Layout

```shell
<project-root>/
  watchlist_parser.py
  config.json                  # independent config (no code changes needed per run)
  <Update Folder>/             # one folder per update
    <the_update_pdf>.pdf
```

- Create **one subfolder per update**.
- Put the **concerned PDF** inside that folder.
- Keep the script and config in the **project root**.

---

## 2) Requirements

- Python 3.9+
- Packages:
  - `PyPDF2` (required)
  - `pandas` + `openpyxl` (only if you want to load the column order from the Excel spec)

Install:

```bash
pip install PyPDF2 pandas openpyxl
```

> If you don’t use the Excel column order, `pandas`/`openpyxl` aren’t required.

---

## 3) Config (`config.json`)

All run-time settings live in the config file. **No code edits** are needed between updates.

### Keys

- `target_folder` (str): the update folder name containing the PDF (e.g., `"MAS ALERT 18 JULY 2025"`)
- `pdf_filename` (str): the PDF name inside the `target_folder`
- `start_page` (int): **1‑indexed** start page (inclusive)
- `end_page` (int): **1‑indexed** end page (inclusive)
- `starting_counter` (int, optional): first number for `WATCHLIST_ID` suffix (default `1`)
- `columns_excel_path` (str, optional): path to the Excel spec (first sheet, `Field` column drives order). If omitted, a baked-in default is used.

### Example

```json
{
  "target_folder": "MAS ALERT 18 JULY 2025",
  "pdf_filename": "AMLD 16-2025 - Circular on Alert List of Persons Involved in Terrorism or Terrorism Financing Activities.pdf",
  "start_page": 4,
  "end_page": 14,
  "starting_counter": 160
}
```

---

## 4) Run

From the project root:

```bash
python watchlist_parser.py --config config.json --project-root .
```

What happens:

1. Reads **pages `start_page`..`end_page`** of `<target_folder>/<pdf_filename>`.
2. Parses rows shaped like: `N.  <Name>  <DOB>  [<Passport>]  <Nationality>` (split on **2+ spaces**; no reformatting).
3. **Verification:** every non‑empty field (Name, Date of Birth, Passport, Nationality) must appear **exactly** in the source text. If any row fails, the script **aborts**; no CSV is written.
4. On success, writes CSV in `<target_folder>/` with name:  
   **`<target_folder>_<YYYYMMDD>.csv`**

---

## 5) Output Columns & Mapping

### Column order

- By default, the script uses a baked-in order derived from the attached Excel.
- Alternatively, set `columns_excel_path` in config to **read the order from the Excel** each run (first sheet, `Field` column).

### Default order (baked-in)

```yaml
WATCHLIST_ID
WATCHLIST_NAME
WATCHLIST_ALIAS
TITLE
SUB_CATEGORY
WATCHLIST_CATEGORY
DATE_OF_BIRTH
WATCHLIST_COUNTRY_OF_BIRTH
WATCHLIST_IDENTIFICATION_NUMBER
WATCHLIST_NATIONALITY
WATCHLIST_GENDER
FURTHER_INFORMATION
WATCHLIST_IDENTIFICATION_COUNTRY
WATCHLIST_IDENTIFICATION_TYPE
NAME_OF_WATCHLIST
WATCHPERSON_RESIDENTIAL_ADDRESS
WATCHLIST_INDIVIDUAL_CORPORATE_TYPE
```

### Field population rules

- `WATCHLIST_ID` → `<FOLDER_NAME_WITH_UNDERSCORES>_<counter>`  
  - Folder name with spaces replaced by `_`.  
  - Counter starts at `starting_counter` (config) and **increments by 1 per row**.
- `WATCHLIST_NAME` → **Name** from PDF
- `WATCHLIST_CATEGORY` → **`TERRORISM OR TERRORISM FINANCING`**
- `DATE_OF_BIRTH` → **DOB** from PDF (exact string; no reformatting)
- `WATCHLIST_IDENTIFICATION_NUMBER` → **Passport** (if available) else leave **blank**
- `WATCHLIST_NATIONALITY` → **Nationality** from PDF
- `NAME_OF_WATCHLIST` → **`MAS_TERRORISM_WATCHLIST`**
- `WATCHLIST_INDIVIDUAL_CORPORATE_TYPE` → **`I`**
- **All other columns** → leave **blank**

---

## 6) Testing & Safety

- The script **always** runs a **full‑field exact‑match verification** for every row before writing output.
- If any field fails to match the source text, the script **stops** and reports mismatches (no file is generated).

---

## 7) Typical Workflow (per update)

1. Create a new update folder: `YYYY MON DD` (or the official alert name).  
   Example: `MAS ALERT 18 JULY 2025/`
2. Drop the alert PDF into that folder.
3. Copy/update `config.json` with:
   - `target_folder`
   - `pdf_filename`
   - `start_page`/`end_page`
   - `starting_counter` (e.g., continue from last run)
4. Run the script.
5. Pick up the CSV in the **same update folder**.

---

## 8) Troubleshooting

- **No entries parsed**  
  - Check `start_page`/`end_page` are **1‑indexed** and correct.  
  - Confirm the PDF rows are one‑line entries (the parser uses `N.` at start of line).
- **Verification failed**  
  - The script will print which SNs failed (up to 50).  
  - Ensure there’s no OCR or hidden characters in the PDF.  
  - Confirm the entry format is still `Name  DOB  [Passport]  Nationality` with **2+ spaces** between columns.
- **Different column order required**  
  - Point `columns_excel_path` to your Excel and keep the order in the `Field` column.

---

## 9) Notes

- The parser is tuned for the **MAS alert list** layout used in your recent circular. If the layout changes (multi‑line entries, joined rows, etc.), we can extend the parser with a “wrapped-line” strategy.
- For deterministic `WATCHLIST_ID`s, control the `starting_counter` in config.

---

## 10) Example Command Recap

```bash
# Using baked-in column order
python watchlist_parser.py --config config.json --project-root .

# Using Excel to drive column order
# (Add "columns_excel_path": "Fave Watchlist format.xlsx" to config.json)
python watchlist_parser.py --config config.json --project-root .
```

---

**Owner:** Product & Risk Ops  
**Scope:** MAS terrorism/TF alert list → Fave Watchlist CSV  
**Accuracy:** Exact-match enforced. No reformatting of values.
