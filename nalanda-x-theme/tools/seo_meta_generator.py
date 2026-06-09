#!/usr/bin/env python3
"""
seo_meta_generator.py — Bulk SEO meta titles/descriptions for Shopify products,
with special handling for ANC / noise-cancelling audio.

It does NOT touch your store. It reads a Shopify product CSV export and writes a
Matrixify-ready import CSV that sets each product's SEO fields (stored in Shopify
as the metafields global.title_tag / global.description_tag).

WORKFLOW
  1. Shopify admin -> Products -> Export -> All products -> CSV.
  2. python3 seo_meta_generator.py products_export.csv "Nalanda Enterprises"
       (2nd arg = brand suffix; optional, default "Nalanda Enterprises")
  3. Review seo_meta_import.csv (Handle, Title, SEO Title, SEO Description,
     Suggested Type, Google Category). Edit anything you want.
  4. Install the FREE "Matrixify" app -> Import -> upload seo_meta_import.csv
     -> it maps the "Metafield: global.title_tag" / "...description_tag" columns
     -> Import. (Or paste values manually for a few products.)
  5. Re-crawl: Google Search Console -> URL Inspection -> Request indexing for
     your key ANC product/collection URLs.

No dependencies. Python 3.8+.

LIMITS (honest): good meta tags improve click-through and relevance, but they do
not guarantee ranking #1 for competitive terms like "ANC buds". Pair this with a
dedicated ANC collection page, real GTINs (see gtin_tools.py), the Google sales
channel/free listings, and — for top placement — Google Shopping/Search Ads.
"""
import csv, sys, os, re

TITLE_MAX = 60          # Google typically shows ~60 chars
DESC_MAX  = 158         # ~155-160 chars

ANC_RE = re.compile(r'\b(anc|active noise|noise[\s-]*cancel)', re.I)

def first_col(cols, *names):
    low = {c.strip().lower(): c for c in cols}
    for n in names:
        if n in low: return low[n]
    return None

def clip(s, n):
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) <= n: return s
    cut = s[:n]
    if ' ' in cut: cut = cut[:cut.rstrip().rfind(' ')]
    return cut.rstrip(' -|,')

def build_title(vendor, title, is_anc, brand):
    base = (vendor + ' ' + title).strip() if vendor and not title.lower().startswith(vendor.lower()) else title
    # ensure the ANC keyword is present for noise-cancelling products
    if is_anc and not ANC_RE.search(base):
        base = base + ' ANC Earbuds'
    t = base
    suffix = ' | ' + brand
    if len(t) + len(suffix) <= TITLE_MAX:
        t = t + suffix
    return clip(t, TITLE_MAX)

def build_desc(vendor, title, price, is_anc, brand):
    anc = "Active Noise Cancellation, " if is_anc else ""
    price_bit = f"From {price}. " if price else ""
    d = (f"Buy {vendor} {title} online in India at {brand}. "
         f"{anc}{price_bit}100% genuine, warranty-backed, COD & fast delivery. Order now.")
    return clip(d, DESC_MAX)

def google_category(text):
    t = text.lower()
    if any(k in t for k in ('earbud', 'tws', 'headphone', 'neckband', 'earphone', 'buds')):
        return "Electronics > Audio > Audio Components > Headphones & Headsets"
    if 'speaker' in t:    return "Electronics > Audio > Audio Components > Speakers"
    if 'watch' in t:      return "Apparel & Accessories > Jewelry > Watches"
    if 'power bank' in t or 'powerbank' in t: return "Electronics > Electronics Accessories > Power > Batteries"
    if any(k in t for k in ('charger', 'cable', 'mouse', 'keyboard')): return "Electronics > Electronics Accessories"
    return "Electronics"

def suggested_type(text, is_anc):
    t = text.lower()
    if 'neckband' in t: return "ANC Neckband" if is_anc else "Neckband"
    if any(k in t for k in ('earbud', 'tws', 'buds', 'earphone')): return "ANC Earbuds" if is_anc else "Earbuds"
    if 'headphone' in t: return "ANC Headphones" if is_anc else "Headphones"
    if 'speaker' in t: return "Bluetooth Speaker"
    if 'watch' in t: return "Smartwatch"
    if 'power bank' in t or 'powerbank' in t: return "Power Bank"
    return ""

def main(path, brand):
    rows = list(csv.DictReader(open(path, newline='', encoding='utf-8-sig')))
    if not rows: print("Empty CSV."); return
    cols = list(rows[0].keys())
    H = first_col(cols, 'handle')
    T = first_col(cols, 'title')
    V = first_col(cols, 'vendor')
    TY = first_col(cols, 'type', 'product type', 'product category')
    TG = first_col(cols, 'tags')
    B = first_col(cols, 'body (html)', 'body html', 'body')
    PR = first_col(cols, 'variant price', 'price')
    if not (H and T): print("CSV needs at least Handle and Title columns (use Shopify export)."); return

    out = []
    seen = set()
    anc_count = 0
    for r in rows:
        handle = (r.get(H) or '').strip()
        title = (r.get(T) or '').strip()
        if not handle or handle in seen: continue   # one row per product (skip image/variant rows)
        if not title: continue
        seen.add(handle)
        vendor = (r.get(V) or '').strip() if V else ''
        tags = (r.get(TG) or '') if TG else ''
        body = (r.get(B) or '') if B else ''
        ptype = (r.get(TY) or '') if TY else ''
        price = (r.get(PR) or '').strip() if PR else ''
        if price and price.replace('.', '', 1).isdigit():
            price = '₹' + price.split('.')[0]

        blob = ' '.join([title, tags, ptype, body])
        is_anc = bool(ANC_RE.search(blob))
        if is_anc: anc_count += 1

        out.append({
            'Handle': handle,
            'Title': title,
            'Metafield: global.title_tag [string]': build_title(vendor, title, is_anc, brand),
            'Metafield: global.description_tag [string]': build_desc(vendor, title, price, is_anc, brand),
            'Type': suggested_type(blob, is_anc),
            'Google Shopping / Google Product Category': google_category(blob),
            'ANC?': 'YES' if is_anc else '',
        })

    fields = ['Handle', 'Title',
              'Metafield: global.title_tag [string]',
              'Metafield: global.description_tag [string]',
              'Type', 'Google Shopping / Google Product Category', 'ANC?']
    with open('seo_meta_import.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)

    print(f"Products processed: {len(out)}")
    print(f"  Detected ANC / noise-cancelling: {anc_count}")
    print("Wrote seo_meta_import.csv  ->  import via Matrixify (or copy values in manually).")
    print("Tip: also create a Collection at /collections/anc-earbuds titled")
    print('     "ANC Earbuds — Active Noise Cancellation" and link it in your menu.')

if __name__ == '__main__':
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        print('Usage: python3 seo_meta_generator.py <products_export.csv> ["Brand suffix"]'); sys.exit(1)
    brand = sys.argv[2] if len(sys.argv) > 2 else 'Nalanda Enterprises'
    main(sys.argv[1], brand)
