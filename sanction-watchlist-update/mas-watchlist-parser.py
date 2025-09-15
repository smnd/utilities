
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watchlist PDF → CSV extractor for MAS alert list pages.

- Reads configuration from a JSON file.
- Parses specified page range in the target folder's PDF.
- Verifies every non-empty field (Name, Date of Birth, Passport, Nationality) exactly matches source text.
- If verification passes, writes a CSV in the required column order.
- Output filename: "<source folder name>_<YYYYMMDD>.csv" saved in the target folder.
- WATCHLIST_ID = "<folder_name_with_underscores>_<counter>" where counter starts from config.starting_counter (default=1).

Dependencies: PyPDF2, pandas (optional if reading column order from Excel).
"""
import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from PyPDF2 import PdfReader
except Exception as e:
    raise SystemExit("PyPDF2 is required. Please install it: pip install PyPDF2") from e

# ---------- Data Model ----------

@dataclass
class Config:
    target_folder: str            # Folder containing the PDF (relative to project root OR absolute)
    pdf_filename: str             # PDF file name inside the target folder
    start_page: int               # 1-indexed inclusive
    end_page: int                 # 1-indexed inclusive
    starting_counter: int = 1     # Starting number for WATCHLIST_ID
    columns_excel_path: Optional[str] = None  # Optional: path to Excel that defines column order
    write_verification_receipt: bool = True

    @staticmethod
    def load(path: Path) -> "Config":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        required = ["target_folder", "pdf_filename", "start_page", "end_page"]
        for k in required:
            if k not in data:
                raise ValueError(f"Missing '{k}' in config JSON")
        return Config(
            target_folder=data["target_folder"],
            pdf_filename=data["pdf_filename"],
            start_page=int(data["start_page"]),
            end_page=int(data["end_page"]),
            starting_counter=int(data.get("starting_counter", 1)),
            columns_excel_path=data.get("columns_excel_path"),
            write_verification_receipt=bool(data.get("write_verification_receipt", True)),
        )

# ---------- Column Order ----------

DEFAULT_OUTPUT_COLUMNS = [
    # This order is derived from the provided "Fave Watchlist format.xlsx" (Field column)
    "WATCHLIST_ID",
    "WATCHLIST_NAME",
    "WATCHLIST_ALIAS",
    "TITLE",
    "SUB_CATEGORY",
    "WATCHLIST_CATEGORY",
    "DATE_OF_BIRTH",
    "WATCHLIST_COUNTRY_OF_BIRTH",
    "WATCHLIST_IDENTIFICATION_NUMBER",
    "WATCHLIST_NATIONALITY",
    "WATCHLIST_GENDER",
    "FURTHER_INFORMATION",
    "WATCHLIST_IDENTIFICATION_COUNTRY",
    "WATCHLIST_IDENTIFICATION_TYPE",
    "NAME_OF_WATCHLIST",
    "WATCHPERSON_RESIDENTIAL_ADDRESS",
    "WATCHLIST_INDIVIDUAL_CORPORATE_TYPE",
]

def load_output_columns_from_excel(xlsx_path: Path) -> List[str]:
    try:
        import pandas as pd
    except Exception as e:
        raise RuntimeError("pandas is required to read column order from Excel. Install via 'pip install pandas openpyxl'.") from e

    df = pd.read_excel(xlsx_path, sheet_name=0)
    if "Field" not in df.columns:
        raise RuntimeError("Excel does not have a 'Field' column to derive output order.")
    cols = [str(x).strip() for x in df["Field"].tolist() if pd.notna(x)]
    if not cols:
        raise RuntimeError("No field names found in 'Field' column.")
    return cols

# ---------- PDF Parsing ----------

SN_LINE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$")
HEADER_PHRASE = "SN Name Date of Birth"

def read_pdf_pages(pdf_path: Path, start_page: int, end_page: int) -> List[str]:
    """
    Returns list of page texts for the inclusive 1-indexed page range.
    """
    reader = PdfReader(str(pdf_path))
    n = len(reader.pages)
    if start_page < 1 or end_page < start_page or end_page > n:
        raise ValueError(f"Invalid page range: {start_page}-{end_page} (document has {n} pages)")
    pages = []
    for i in range(start_page-1, end_page):
        txt = reader.pages[i].extract_text() or ""
        pages.append(txt)
    return pages

def parse_entries_from_pages(pages_texts: List[str]) -> List[Tuple[str, str, str, str, str]]:
    """
    Parse lines that look like:
        'N.  <Name>  <DOB>  [<Passport>]  <Nationality>'
    Splits on 2+ spaces to preserve exact token strings within columns.
    Returns a list of tuples: (SN, Name, Date of Birth, Passport, Nationality)
    """
    entries: List[Tuple[str, str, str, str, str]] = []
    for page_text in pages_texts:
        for raw_ln in page_text.splitlines():
            ln = raw_ln.strip()
            if not ln or HEADER_PHRASE in ln:
                continue
            m = SN_LINE_RE.match(ln)
            if not m:
                continue
            sn = m.group(1).strip()
            rest = m.group(2)

            # Split into columns; expect 3 or 4 parts
            parts = re.split(r"\s{2,}", rest.strip())
            name = dob = passport = nationality = ""

            if len(parts) == 3:
                name, dob, nationality = parts
            elif len(parts) == 4:
                name, dob, passport, nationality = parts
            else:
                # Fallback: find DOB and split around it
                dob_match = re.search(r"\b(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\b", rest)
                if dob_match:
                    dob = dob_match.group(1)
                    name = rest[:dob_match.start()].strip()
                    tail = re.split(r"\s{2,}", rest[dob_match.end():].strip())
                    if len(tail) >= 2:
                        passport, nationality = tail[0], tail[1]
                    elif len(tail) == 1:
                        passport = ""
                        nationality = tail[0]
                else:
                    # Unparseable line; skip
                    continue

            entries.append((sn, name.strip(), dob.strip(), passport.strip(), nationality.strip()))
    # sort by SN numeric to keep consistent order
    entries.sort(key=lambda x: int(x[0]))
    return entries

# ---------- Verification ----------

def verify_entries_exact(entries: List[Tuple[str, str, str, str, str]], pages_texts: List[str]) -> Dict[str, int]:
    """
    Each non-empty field must appear as an exact substring in the concatenated pages text.
    Returns per-field totals: OK/MISMATCH/SKIP. Raises ValueError if any mismatch found.
    """
    concat_text = "\n".join(pages_texts)
    fields = ["Name", "Date of Birth", "Passport", "Nationality"]
    totals = {f: {"OK": 0, "MISMATCH": 0, "SKIP": 0} for f in fields}
    mismatches = []

    for sn, name, dob, passport, nationality in entries:
        checks = []
        for label, value in [("Name", name), ("Date of Birth", dob), ("Passport", passport), ("Nationality", nationality)]:
            if value == "":
                totals[label]["SKIP"] += 1
                checks.append((label, "SKIP"))
            else:
                if value in concat_text:
                    totals[label]["OK"] += 1
                    checks.append((label, "OK"))
                else:
                    totals[label]["MISMATCH"] += 1
                    checks.append((label, "MISMATCH"))
        if any(s == "MISMATCH" for _, s in checks):
            mismatches.append((sn, name, checks))

    if mismatches:
        # Build readable error
        lines = ["Verification failed. Mismatches found:"]
        for sn, name, checks in mismatches[:50]:
            status = ", ".join([f"{lbl}:{st}" for lbl, st in checks])
            lines.append(f"SN {sn} — {name} -> {status}")
        lines.append("(showing up to 50 mismatches)")
        raise ValueError("\n".join(lines))

    return {f"{k}_OK": v["OK"] for k, v in totals.items()} | {f"{k}_SKIP": v["SKIP"] for k, v in totals.items()}

# ---------- Mapping to Output ----------

def make_watchlist_id_prefix(folder_name: str) -> str:
    return re.sub(r"\s+", "_", folder_name.strip())

def map_entries_to_output_rows(
    entries: List[Tuple[str, str, str, str, str]],
    output_columns: List[str],
    folder_name: str,
    starting_counter: int,
) -> List[Dict[str, str]]:
    """
    Create rows with required columns in the exact order.
    - WATCHLIST_ID = <folder_name_with_underscores>_<counter>
    - WATCHLIST_NAME = Name
    - WATCHLIST_CATEGORY = "TERRORISM OR TERRORISM FINANCING"
    - DATE_OF_BIRTH = Date of Birth
    - WATCHLIST_IDENTIFICATION_NUMBER = Passport (if any)
    - WATCHLIST_NATIONALITY = Nationality
    - NAME_OF_WATCHLIST = "MAS_TERRORISM_WATCHLIST"
    - WATCHLIST_INDIVIDUAL_CORPORATE_TYPE = "I"
    - Keep all other columns blank.
    """
    prefix = make_watchlist_id_prefix(folder_name)
    rows: List[Dict[str, str]] = []
    counter = starting_counter

    for sn, name, dob, passport, nationality in entries:
        row = {col: "" for col in output_columns}
        row["WATCHLIST_ID"] = f"{prefix}_{counter}"
        row["WATCHLIST_NAME"] = name
        row["WATCHLIST_CATEGORY"] = "TERRORISM OR TERRORISM FINANCING"
        row["DATE_OF_BIRTH"] = dob
        row["WATCHLIST_IDENTIFICATION_NUMBER"] = passport
        row["WATCHLIST_NATIONALITY"] = nationality
        row["NAME_OF_WATCHLIST"] = "MAS_TERRORISM_WATCHLIST"
        row["WATCHLIST_INDIVIDUAL_CORPORATE_TYPE"] = "I"
        rows.append(row)
        counter += 1

    return rows

# ---------- Orchestration ----------

def run(config_path: Path, project_root: Path) -> Path:
    cfg = Config.load(config_path)

    # Resolve target folder and PDF
    target_dir = (project_root / cfg.target_folder) if not Path(cfg.target_folder).is_absolute() else Path(cfg.target_folder)
    pdf_path = target_dir / cfg.pdf_filename
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    # Determine output columns
    if cfg.columns_excel_path:
        cols_path = Path(cfg.columns_excel_path)
        if not cols_path.is_absolute():
            cols_path = project_root / cols_path
        output_columns = load_output_columns_from_excel(cols_path)
    else:
        output_columns = DEFAULT_OUTPUT_COLUMNS

    # Read and parse
    pages_texts = read_pdf_pages(pdf_path, cfg.start_page, cfg.end_page)
    entries = parse_entries_from_pages(pages_texts)

    if not entries:
        raise ValueError("No entries parsed from the given pages. Check page range and PDF structure.")

    # Verify exact matches before writing
    totals = verify_entries_exact(entries, pages_texts)

    # ---- Confirmation message ----
    # Mismatches would have raised above; reaching here implies success.
    def _t(label: str) -> str:
        ok = totals.get(f"{label}_OK", 0)
        skip = totals.get(f"{label}_SKIP", 0)
        return f"{label}: OK={ok}, SKIP={skip}"

    confirm_msg = (
        f"Verification PASSED for {len(entries)} rows.\n"
        f"Per-field totals -> {_t('Name')}; {_t('Date of Birth')}; {_t('Passport')}; {_t('Nationality')}"
    )
    print(confirm_msg, flush=True)

    # Optionally write a verification receipt next to the PDF/CSV
    if cfg.write_verification_receipt:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        receipt_path = target_dir / "verification_OK.txt"
        receipt_path.write_text(
            f"{confirm_msg}\n"
            f"Timestamp: {timestamp}\n"
            f"Source PDF: {pdf_path.name}\n"
            f"Pages: {cfg.start_page}-{cfg.end_page}\n",
            encoding="utf-8"
        )

    # Map to output rows
    rows = map_entries_to_output_rows(entries, output_columns, cfg.target_folder, cfg.starting_counter)

    # Output file: <source folder name>_<YYYYMMDD>.csv in target folder
    date_str = datetime.now().strftime("%Y%m%d")
    out_name = f"{cfg.target_folder}_{date_str}.csv"
    out_path = target_dir / out_name

    # Write CSV with the exact column order
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return out_path

def main():
    parser = argparse.ArgumentParser(description="Extract MAS alert list watchlist entries to CSV.")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--project-root", default=".", help="Project root path (default: current dir)")
    args = parser.parse_args()

    out_path = run(Path(args.config), Path(args.project_root))
    print(f"CSV generated: {out_path}")

if __name__ == "__main__":
    main()
