// Apply optimized content back to Shopify.
// Reads changes.csv (produced/edited by you or by Claude) and updates products.
//
// Usage:
//   node apply.mjs            -> DRY RUN (shows what would change, writes nothing)
//   node apply.mjs --apply    -> actually push changes to Shopify
//   node apply.mjs --file=my-changes.csv [--apply]
//
// changes.csv columns (header row required; leave a cell blank to skip that field):
//   handle, seo_title, seo_description, product_type, tags, body_html, barcode
//   - tags: comma-or-pipe separated, e.g. "phone|android|5g"
//   - barcode (GTIN/UPC/EAN): applied to the variant ONLY for single-variant products
//     (multi-variant barcodes need a separate per-variant file; the script will warn).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gql } from "./lib/shopify.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const APPLY = args.includes("--apply");
const fileArg = args.find((a) => a.startsWith("--file="));
const FILE = fileArg ? fileArg.split("=")[1] : "changes.csv";

// --- tiny CSV parser (handles quoted fields, commas, newlines) ---
function parseCsv(text) {
  const rows = [];
  let row = [], cell = "", inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { cell += '"'; i++; }
        else inQuotes = false;
      } else cell += c;
    } else {
      if (c === '"') inQuotes = true;
      else if (c === ",") { row.push(cell); cell = ""; }
      else if (c === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
      else if (c === "\r") { /* ignore */ }
      else cell += c;
    }
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

function readChanges(file) {
  const full = path.isAbsolute(file) ? file : path.join(__dirname, file);
  if (!fs.existsSync(full)) {
    console.error(`\nChanges file not found: ${full}\n` +
      `Create it (see header format in apply.mjs) or pass --file=path.csv\n`);
    process.exit(1);
  }
  const rows = parseCsv(fs.readFileSync(full, "utf8")).filter((r) => r.some((c) => c.trim() !== ""));
  const headers = rows.shift().map((h) => h.trim());
  return rows.map((r) => {
    const obj = {};
    headers.forEach((h, i) => (obj[h] = (r[i] || "").trim()));
    return obj;
  });
}

const PRODUCT_BY_HANDLE = `
  query($handle: String!) {
    productByHandle(handle: $handle) {
      id
      title
      variants(first: 50) { nodes { id barcode } }
    }
  }`;

const PRODUCT_UPDATE = `
  mutation($input: ProductInput!) {
    productUpdate(input: $input) {
      product { id }
      userErrors { field message }
    }
  }`;

const VARIANTS_UPDATE = `
  mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
    productVariantsBulkUpdate(productId: $productId, variants: $variants) {
      productVariants { id barcode }
      userErrors { field message }
    }
  }`;

async function main() {
  const changes = readChanges(FILE);
  console.log(`\n${APPLY ? "APPLYING" : "DRY RUN"} — ${changes.length} rows from ${FILE}\n`);

  let updated = 0, skipped = 0, errors = 0;

  for (const ch of changes) {
    if (!ch.handle) { skipped++; continue; }

    const data = await gql(PRODUCT_BY_HANDLE, { handle: ch.handle });
    const product = data.productByHandle;
    if (!product) {
      console.log(`  ! not found: ${ch.handle}`);
      errors++;
      continue;
    }

    const input = { id: product.id };
    const seo = {};
    if (ch.seo_title) seo.title = ch.seo_title;
    if (ch.seo_description) seo.description = ch.seo_description;
    if (Object.keys(seo).length) input.seo = seo;
    if (ch.product_type) input.productType = ch.product_type;
    if (ch.body_html) input.descriptionHtml = ch.body_html;
    if (ch.tags) input.tags = ch.tags.split(/[|,]/).map((t) => t.trim()).filter(Boolean);

    const fields = Object.keys(input).filter((k) => k !== "id");
    console.log(`  ${ch.handle}  ->  [${fields.join(", ") || "no product fields"}]` +
      (ch.barcode ? `  barcode=${ch.barcode}` : ""));

    if (APPLY) {
      if (fields.length) {
        const res = await gql(PRODUCT_UPDATE, { input });
        const errs = res.productUpdate.userErrors;
        if (errs.length) { console.log(`     product errors: ${JSON.stringify(errs)}`); errors++; }
      }
      if (ch.barcode) {
        const variants = product.variants.nodes;
        if (variants.length === 1) {
          const res = await gql(VARIANTS_UPDATE, {
            productId: product.id,
            variants: [{ id: variants[0].id, barcode: ch.barcode }],
          });
          const errs = res.productVariantsBulkUpdate.userErrors;
          if (errs.length) { console.log(`     variant errors: ${JSON.stringify(errs)}`); errors++; }
        } else {
          console.log(`     ! skipped barcode: ${variants.length} variants (needs per-variant file)`);
        }
      }
    }
    updated++;
  }

  console.log(`\nDone. ${updated} processed, ${skipped} skipped, ${errors} errors.`);
  if (!APPLY) console.log(`This was a DRY RUN. Re-run with --apply to push changes.\n`);
}

main().catch((e) => { console.error(e); process.exit(1); });
