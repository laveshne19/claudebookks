#!/usr/bin/env python3
"""
gtin_tools.py — Bulk GTIN/barcode QA for a Shopify product export.

WHY: Google Merchant Center maps Shopify's "Variant Barcode" field to `gtin`.
A wrong/invalid GTIN gets a product disapproved (or the account suspended), so
every barcode must have a valid check digit. This script does NOT invent GTINs —
it only validates the ones you provide and tells you exactly what's missing.

WORKFLOW
  1. Shopify admin -> Products -> Export -> "All products" -> CSV (plain).
  2. Open the CSV, fill the "Variant Barcode" column with each product's real
     UPC/EAN/GTIN (from the box, the manufacturer, or the Amazon listing — your
     SKUs like B0CQN2BHW8 are Amazon ASINs, so the GTIN is on that Amazon page).
  3. Run:  python3 gtin_tools.py products_export.csv
  4. It writes:
       - gtin_report.csv  -> every row, with STATUS (OK / MISSING / INVALID) + reason
       - gtin_clean.csv    -> import-ready copy with barcodes normalised (only valid ones)
  5. Fix anything flagged, then Shopify -> Products -> Import (overwrite existing).
  6. In the Google sales channel, re-sync. Done.

No dependencies. Python 3.8+.
"""
import csv, sys, os

def gtin_check_ok(code: str) -> bool:
    """Validate GTIN-8/12/13/14 using the standard mod-10 check digit."""
    if not code.isdigit():
        return False
    if len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    check = digits[-1]
    body = digits[:-1][::-1]               # right-to-left, excluding check digit
    total = 0
    for i, d in enumerate(body):
        total += d * (3 if i % 2 == 0 else 1)
    calc = (10 - (total % 10)) % 10
    return calc == check

def normalise(code: str) -> str:
    """Strip spaces; pad a 12-digit UPC to 13-digit EAN (Google prefers GTIN-13/14)."""
    code = (code or "").strip().replace(" ", "").replace("-", "")
    if code and code.isdigit() and len(code) == 12 and gtin_check_ok(code):
        return "0" + code   # UPC-A -> GTIN-13
    return code

def main(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print("Empty CSV."); return
    cols = list(rows[0].keys())
    bcol = next((c for c in cols if c.strip().lower() in ("variant barcode", "barcode")), None)
    if not bcol:
        print("No 'Variant Barcode' column found. Export the plain Shopify product CSV.")
        return

    title_col = next((c for c in cols if c.strip().lower() == "title"), cols[0])
    sku_col = next((c for c in cols if c.strip().lower() in ("variant sku", "sku")), None)

    ok = miss = bad = 0
    report_rows = []
    for r in rows:
        # only consider rows that represent a variant (have a barcode cell concept)
        raw = (r.get(bcol) or "").strip()
        norm = normalise(raw)
        if not raw:
            # blank barcode lines are often the extra image rows in Shopify export; skip empties with no title
            if not (r.get(title_col) or "").strip():
                continue
            status, reason = "MISSING", "no barcode entered"
            miss += 1
        elif gtin_check_ok(norm):
            status, reason = "OK", ""
            r[bcol] = norm
            ok += 1
        else:
            status, reason = "INVALID", "check digit / length failed — verify the real GTIN"
            bad += 1
        report_rows.append({
            "Title": (r.get(title_col) or "").strip(),
            "SKU": (r.get(sku_col) or "").strip() if sku_col else "",
            "Barcode": raw, "Normalised": norm, "STATUS": status, "Reason": reason,
        })

    with open("gtin_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Title", "SKU", "Barcode", "Normalised", "STATUS", "Reason"])
        w.writeheader(); w.writerows(report_rows)

    # clean import copy: keep original file shape, normalised valid barcodes only
    with open("gtin_clean.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            n = normalise((r.get(bcol) or "").strip())
            r[bcol] = n if gtin_check_ok(n) else (r.get(bcol) or "")
            w.writerow(r)

    print(f"Rows checked: {ok + miss + bad}")
    print(f"  OK:      {ok}")
    print(f"  MISSING: {miss}  (need a real GTIN added)")
    print(f"  INVALID: {bad}   (wrong number — do NOT push to Google)")
    print("\nWrote gtin_report.csv (review) and gtin_clean.csv (import-ready).")
    if bad:
        print("\n⚠️  Fix INVALID rows before importing — Google rejects bad GTINs.")

if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.exists(sys.argv[1]):
        print("Usage: python3 gtin_tools.py <shopify_products_export.csv>")
        sys.exit(1)
    main(sys.argv[1])
