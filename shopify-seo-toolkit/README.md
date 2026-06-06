# GoGadget Shopify SEO Toolkit

Audit and bulk-optimize your Shopify store (gogadget.co.in) for Google ranking:
SEO meta titles/descriptions, GTIN/barcodes, product types, tags, descriptions and
image alt text — across all 100+ products.

No libraries to install. You only need **Node.js** (v18 or newer).

---

## One-time setup

1. **Install Node.js** (if you don't have it): https://nodejs.org (pick the LTS version).
   Check it works — open a terminal and run:
   ```
   node --version
   ```

2. **Get the files** onto your computer (this `shopify-seo-toolkit` folder).

3. **Create your secrets file.** In this folder, copy `.env.example` to `.env`
   and fill in your values:
   ```
   SHOPIFY_STORE=your-store.myshopify.com
   SHOPIFY_ADMIN_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxx
   ```
   - `SHOPIFY_STORE` is your **myshopify.com** domain (not gogadget.co.in).
   - `SHOPIFY_ADMIN_TOKEN` is the **Admin API access token** from your custom app
     (Settings → Apps and sales channels → Develop apps → your app → API credentials).
   - The `.env` file is git-ignored and stays only on your computer. **Never share it.**

4. **Required app scopes** (in your custom app → Configuration → Admin API scopes):
   `read_products`, `write_products`. Re-install the app after changing scopes.

---

## Step 1 — Audit (read-only, safe)

```
node audit.mjs
```

This produces:
- **`audit-report.csv`** — open in Excel/Google Sheets to see every product and what's
  missing (meta title, GTIN, alt text, thin description, etc.).
- **`products-export.json`** — the full data. **Upload this file to Claude** and it will
  generate premium, keyword-rich, Apple/Amazon-style content for every product and hand
  you back a ready-to-apply `changes.csv`.

## Step 2 — Review the changes

Open the `changes.csv` (the one Claude gives you, or the included sample). Each row is one
product, matched by `handle`. Edit anything you like. Columns:

| column          | meaning                                                        |
|-----------------|----------------------------------------------------------------|
| handle          | product handle (the URL slug) — used to match the product      |
| seo_title       | meta title for Google (≤ 60 chars)                             |
| seo_description | meta description for Google (70–160 chars)                     |
| product_type    | e.g. "Smartphone", "Wireless Earbuds"                          |
| tags            | keywords, separated by `|` e.g. `5g|android|budget phone`      |
| body_html       | full product description (HTML allowed)                        |
| barcode         | GTIN / UPC / EAN (single-variant products)                     |

Leave a cell blank to leave that field unchanged.

## Step 3 — Dry run (still safe, changes nothing)

```
node apply.mjs
```
Shows exactly what would change for each product.

## Step 4 — Apply for real

```
node apply.mjs --apply
```
Pushes the changes to your live store. Re-run `node audit.mjs` afterwards to confirm the
issue counts dropped.

---

## Notes
- The toolkit paces itself to respect Shopify's API rate limits, so large catalogs may
  take a few minutes.
- Multi-variant barcodes (e.g. a phone in several colors with different GTINs) need a
  per-variant file — ask Claude to generate one if you have those.
- This handles **product data SEO**. The storefront look (Apple/Amazon-style theme),
  technical SEO (schema, sitemaps, Search Console, Merchant Center) and content writing
  are handled separately — see the project plan.
