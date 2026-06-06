// Audit all products and report SEO / GTIN / content gaps.
// Usage: node audit.mjs
// Outputs:
//   - audit-report.csv      (human-readable issue list, open in Excel/Sheets)
//   - products-export.json   (full data; upload this to Claude for content generation)

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fetchAllProducts, toCsv } from "./lib/shopify.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const stripHtml = (html) => (html || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

function auditProduct(p) {
  const issues = [];
  const bodyText = stripHtml(p.descriptionHtml);
  const variants = p.variants?.nodes || [];
  const images = p.images?.nodes || [];

  if (!p.seo?.title) issues.push("missing_meta_title");
  else if (p.seo.title.length > 60) issues.push("meta_title_too_long");

  if (!p.seo?.description) issues.push("missing_meta_description");
  else if (p.seo.description.length < 70 || p.seo.description.length > 160)
    issues.push("meta_description_bad_length");

  if (bodyText.length < 200) issues.push("thin_description");
  if (!p.productType) issues.push("missing_product_type");
  if (!p.vendor) issues.push("missing_vendor");
  if (!p.tags || p.tags.length === 0) issues.push("no_tags");

  const missingBarcode = variants.filter((v) => !v.barcode).length;
  if (missingBarcode > 0) issues.push(`missing_gtin_barcode(${missingBarcode}/${variants.length})`);

  const missingSku = variants.filter((v) => !v.sku).length;
  if (missingSku > 0) issues.push(`missing_sku(${missingSku}/${variants.length})`);

  const missingAlt = images.filter((i) => !i.altText).length;
  if (missingAlt > 0) issues.push(`missing_image_alt(${missingAlt}/${images.length})`);

  if (images.length === 0) issues.push("no_images");

  return {
    handle: p.handle,
    title: p.title,
    status: p.status,
    product_type: p.productType || "",
    vendor: p.vendor || "",
    num_variants: variants.length,
    num_images: images.length,
    meta_title_len: p.seo?.title?.length || 0,
    meta_desc_len: p.seo?.description?.length || 0,
    body_text_len: bodyText.length,
    issue_count: issues.length,
    issues: issues.join("; "),
    admin_url: `https://${process.env.SHOPIFY_STORE}/admin/products/${p.id.split("/").pop()}`,
  };
}

async function main() {
  console.log("Connecting to Shopify and fetching products...\n");
  const products = await fetchAllProducts();

  const rows = products.map(auditProduct).sort((a, b) => b.issue_count - a.issue_count);

  const headers = [
    "handle", "title", "status", "product_type", "vendor",
    "num_variants", "num_images", "meta_title_len", "meta_desc_len",
    "body_text_len", "issue_count", "issues", "admin_url",
  ];
  const csv = toCsv(rows, headers);
  fs.writeFileSync(path.join(__dirname, "audit-report.csv"), csv);

  // Trim export to what's needed for content generation.
  const exportData = products.map((p) => ({
    id: p.id,
    handle: p.handle,
    title: p.title,
    status: p.status,
    productType: p.productType,
    vendor: p.vendor,
    tags: p.tags,
    descriptionHtml: p.descriptionHtml,
    seo: p.seo,
    variants: (p.variants?.nodes || []).map((v) => ({
      id: v.id, sku: v.sku, barcode: v.barcode, title: v.title, price: v.price,
    })),
    images: (p.images?.nodes || []).map((i) => ({ id: i.id, altText: i.altText })),
  }));
  fs.writeFileSync(
    path.join(__dirname, "products-export.json"),
    JSON.stringify(exportData, null, 2)
  );

  // Summary
  const tally = {};
  for (const r of rows) {
    for (const i of r.issues.split("; ").filter(Boolean)) {
      const key = i.replace(/\(.*\)/, "");
      tally[key] = (tally[key] || 0) + 1;
    }
  }
  console.log(`\n=== AUDIT SUMMARY (${products.length} products) ===`);
  console.log(`Products with at least one issue: ${rows.filter((r) => r.issue_count > 0).length}\n`);
  for (const [k, v] of Object.entries(tally).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${String(v).padStart(4)}  ${k}`);
  }
  console.log(`\nWrote audit-report.csv  (open in Excel/Google Sheets)`);
  console.log(`Wrote products-export.json  (upload this to Claude for content generation)\n`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
