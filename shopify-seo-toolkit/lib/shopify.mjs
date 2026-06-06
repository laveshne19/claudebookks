// Minimal, dependency-free Shopify Admin GraphQL client.
// Handles auth, .env loading, pagination and rate-limit (throttle) back-off.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Load KEY=VALUE pairs from a .env file into process.env (does not override existing). */
export function loadEnv(file = path.join(__dirname, "..", ".env")) {
  if (!fs.existsSync(file)) return;
  const text = fs.readFileSync(file, "utf8");
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = val;
  }
}

export function getConfig() {
  loadEnv();
  const store = (process.env.SHOPIFY_STORE || "").trim();
  const token = (process.env.SHOPIFY_ADMIN_TOKEN || "").trim();
  const version = (process.env.SHOPIFY_API_VERSION || "2024-10").trim();

  if (!store || !token) {
    console.error(
      "\nMissing config. Copy .env.example to .env and fill in SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN.\n"
    );
    process.exit(1);
  }
  if (!store.endsWith(".myshopify.com")) {
    console.error(
      `\nSHOPIFY_STORE should be your *.myshopify.com domain, got: "${store}"\n`
    );
    process.exit(1);
  }
  if (!token.startsWith("shpat_")) {
    console.warn(
      "\nWarning: SHOPIFY_ADMIN_TOKEN does not start with 'shpat_'. " +
        "Make sure you used the Admin API access token, not the API key/secret.\n"
    );
  }
  return { store, token, version };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Run a GraphQL query/mutation against the Admin API.
 * Retries on throttling and transient network errors with back-off.
 */
export async function gql(query, variables = {}, attempt = 1) {
  const { store, token, version } = getConfig();
  const url = `https://${store}/admin/api/${version}/graphql.json`;

  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
      },
      body: JSON.stringify({ query, variables }),
    });
  } catch (err) {
    if (attempt <= 4) {
      const wait = 2000 * attempt;
      console.warn(`Network error (${err.message}); retrying in ${wait}ms...`);
      await sleep(wait);
      return gql(query, variables, attempt + 1);
    }
    throw err;
  }

  if (res.status === 429 && attempt <= 6) {
    const wait = 2000 * attempt;
    console.warn(`Rate limited (429); waiting ${wait}ms...`);
    await sleep(wait);
    return gql(query, variables, attempt + 1);
  }

  if (res.status === 401 || res.status === 403) {
    console.error(
      `\nAuth failed (HTTP ${res.status}). Check your Admin API access token and that ` +
        `the app has the required scopes (read_products, write_products).\n`
    );
    process.exit(1);
  }

  const json = await res.json();

  // GraphQL-level throttling
  const throttled =
    json.errors &&
    json.errors.some((e) => e.extensions && e.extensions.code === "THROTTLED");
  if (throttled && attempt <= 6) {
    const wait = 2000 * attempt;
    console.warn(`GraphQL throttled; waiting ${wait}ms...`);
    await sleep(wait);
    return gql(query, variables, attempt + 1);
  }

  if (json.errors) {
    throw new Error("GraphQL error: " + JSON.stringify(json.errors, null, 2));
  }

  // Gentle pacing using the leaky-bucket status when available.
  const cost = json.extensions && json.extensions.cost;
  if (cost && cost.throttleStatus) {
    const { currentlyAvailable, restoreRate } = cost.throttleStatus;
    if (currentlyAvailable < 100) {
      await sleep(Math.ceil((100 - currentlyAvailable) / restoreRate) * 1000);
    }
  }

  return json.data;
}

/** Fetch every product (with variants & images) using cursor pagination. */
export async function fetchAllProducts() {
  const products = [];
  let cursor = null;
  let page = 0;

  const query = `
    query Products($cursor: String) {
      products(first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          title
          handle
          status
          productType
          vendor
          tags
          descriptionHtml
          seo { title description }
          featuredImage { id url altText }
          images(first: 20) { nodes { id altText } }
          variants(first: 50) {
            nodes { id sku barcode title price }
          }
        }
      }
    }`;

  do {
    page++;
    const data = await gql(query, { cursor });
    const conn = data.products;
    products.push(...conn.nodes);
    process.stdout.write(`\rFetched ${products.length} products (page ${page})...`);
    cursor = conn.pageInfo.hasNextPage ? conn.pageInfo.endCursor : null;
  } while (cursor);

  process.stdout.write("\n");
  return products;
}

/** CSV-escape a single field. */
export function csvCell(value) {
  const s = value == null ? "" : String(value);
  if (/[",\n]/.test(s)) return '"' + s.replace(/"/g, '""') + '"';
  return s;
}

export function toCsv(rows, headers) {
  const lines = [headers.map(csvCell).join(",")];
  for (const row of rows) {
    lines.push(headers.map((h) => csvCell(row[h])).join(","));
  }
  return lines.join("\n");
}
