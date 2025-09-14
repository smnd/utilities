import csv
import dns.resolver
import sys

def check_mx_records(domain):
    """Check MX records for the given domain and return (has_mx, error_reason)."""
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return True, None
    except dns.resolver.NoAnswer:
        return False, "NoAnswer: No MX record found"
    except dns.resolver.NXDOMAIN:
        return False, "NXDOMAIN: Domain does not exist"
    except dns.resolver.Timeout:
        return False, "Timeout: Query timed out"
    except dns.resolver.NoNameservers:
        return False, "NoNameservers: All nameservers failed to answer"
    except Exception as e:
        # Catch-all for any other DNS-related exceptions
        return False, str(e)


def process_csv(input_file, output_file):
    """Reads a CSV containing domain names, checks for MX records, and writes the results along with any error.
    Shows a single-line progress display that updates as each domain is checked."""
    with open(input_file, 'r', newline='') as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)  # convert to list for easier counting

    total_rows = len(rows)

    # Prepare the output CSV
    with open(output_file, 'w', newline='') as f_out:
        # Add two new columns: "has_mx_record" and "mx_error_reason".
        if rows:
            fieldnames = list(rows[0].keys()) + ["has_mx_record", "mx_error_reason"]
        else:
            fieldnames = ["domain", "has_mx_record", "mx_error_reason"]

        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(rows, start=1):
            domain = row.get("domain", "").strip()

            # Update single-line progress in console
            sys.stdout.write(f"\r\nChecking domain {i}/{total_rows}: {domain}")
            sys.stdout.flush()


            if not domain:
                row["has_mx_record"] = "Invalid domain"
                row["mx_error_reason"] = "No domain provided"
            else:
                valid_mx, error_reason = check_mx_records(domain)
                row["has_mx_record"] = "Yes" if valid_mx else "No"
                row["mx_error_reason"] = error_reason if error_reason else ""

            writer.writerow(row)

    # Print final newline and summary
    print(f"\nDone! Processed all {total_rows} domains.")

if __name__ == "__main__":
    # Change file names as needed with full paths
    input_file = "domains.csv"
    output_file = "domains_output.csv"
    
    process_csv(input_file, output_file)