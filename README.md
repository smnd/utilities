# Utilities Workspace

A curated collection of small, task-focused tools that live outside larger services. Each subfolder ships with its own README for setup, usage, and maintenance notes.

## Current Utilities

- **MX Record Checker** — Processes a CSV of domains and flags which ones publish MX records, including failure reasons for DNS lookups. [Read more](mx-record-checker/README.md)
- **MAS Watchlist PDF Extractor** — Converts MAS alert list PDFs into Fave Watchlist–ready CSV files with exact-match validation, so mismatched rows never slip through. [Read more](sanction-watchlist-update/README.md)
- **SGQR Generator** — Builds SGQR-compliant payment QR codes from a JSON config, handling TLV encoding, validation, and QR image output. [Read more](sgqr-generator/README.md)

---

_Add new utilities as folders in this directory, and mirror the format above with a short summary plus a link to their detailed README._
