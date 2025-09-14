# MX Record Checker

A tiny Python utility that reads domains from a CSV, checks whether they have **MX records**, and writes results (including error reasons) to a new CSV. Progress prints as it goes. This can be used to check valid email domains during user registration or later database cleanup.  

---

## Requirements

- Python 3.8+
- [dnspython](https://www.dnspython.org/) (`pip install dnspython`)

---

## Quick start

```bash
# 1) Create & activate a virtual env (recommended)
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell

# 2) Install dependency (inside the venv)
python -m pip install dnspython

# 3) Run (uses default files)
python mx-record-checker.py
```

### Default files

- Input: `domains.csv`
- Output: `domains_output.csv`

> To change filenames, edit the call at the bottom of `mx-record-checker.py`:
>
> ```python
> if __name__ == "__main__":
>     process_csv("my_input.csv", "my_output.csv")
> ```

---

## CSV formats

### Input

The input CSV must contain a header named `domain`:

```csv
domain
example.com
no-such-domain.tld
```

### Output

Two columns are added to the original rows:

| Column             | Meaning                                                                 |
|--------------------|-------------------------------------------------------------------------|
| `has_mx_record`    | `"Yes"` if at least one MX is found, `"No"` if none, or `"Invalid domain"` if the `domain` cell was empty. |
| `mx_error_reason`  | Empty on success; otherwise the reason (e.g., `NXDOMAIN`, `NoAnswer`, `Timeout`). |

Example output:

```csv
domain,has_mx_record,mx_error_reason
example.com,Yes,
no-such-domain.tld,No,NXDOMAIN: Domain does not exist
,Invalid domain,No domain provided
```

---

## How it works

For each domain, the script calls `dns.resolver.resolve(domain, 'MX')` and classifies common failure cases:

- `NoAnswer` → no MX record found
- `NXDOMAIN` → domain doesn’t exist
- `Timeout` → query timed out
- `NoNameservers` → all nameservers failed to answer
- Any other exception → captured as a string in `mx_error_reason`

A single-line progress message updates as each domain is checked; a summary prints at the end.

---

## Troubleshooting

- **ImportError: No module named `dns`**  
  Activate your venv or run with it explicitly:

  ```bash
  source .venv/bin/activate
  python -m pip install dnspython
  python mx-record-checker.py
  ```

  In VS Code: *Python: Select Interpreter* → choose `./.venv/bin/python`.

- **All domains fail with Timeout/NoNameservers**  
  You may be behind a firewall/VPN or your DNS is unreachable. Try again on a different network or fix system resolvers.

- **Name shadowing**  
  Ensure you don’t have a local `dns.py` or `dns/` folder that would hide the real package.

---

## Development

```bash
# Freeze dependencies for reproducibility
python -m pip freeze > requirements.txt

# (Optional) basic structure if you refactor later
# mx_record_checker/
#   __init__.py
#   core.py       # check_mx_records / process_csv
#   cli.py        # optional CLI wrapper
```

---

## Notes & limitations

- Some servers accept mail via A/AAAA fallback when MX is absent; this tool strictly reports MX presence only.
- No domain syntax validation beyond DNS lookup.
- The utility is read-only; it does not modify DNS.

---

## License

MIT
