# Nalanda Enterprises — Professional Product Page Kit

A drop-in set of Shopify **Online Store 2.0** sections that turn a cluttered
product page into a clean, conversion-focused, boAt/Amazon-style layout —
without touching your existing theme code.

## What's included (`shopify-theme/sections/`)

| File | What it adds |
|---|---|
| `product-pro-details.liquid` | Feature highlights, trust badges, specifications table, FAQ accordion |
| `product-pro-reviews.liquid`  | Clean Judge.me reviews block (star summary + full reviews) |
| `product-sticky-atc.liquid`   | Sticky "Add to Cart" bar that follows the shopper (big mobile win) |

All text/blocks are editable in the **Theme Editor** — no coding after install.
Colours and fonts inherit from your theme, so it looks native.

---

## Install (≈5 minutes, one-time)

1. Shopify admin → **Online Store → Themes**.
2. **Duplicate your live theme first** (⋯ → Duplicate) so the original stays safe.
3. On the duplicate: **⋯ → Edit code**.
4. Left sidebar → **Sections → Add a new section**. Create three sections, naming
   them exactly (no `.liquid` suffix needed):
   - `product-pro-details`
   - `product-pro-reviews`
   - `product-sticky-atc`
   For each: delete the starter content, paste the matching file, **Save**.
5. Back to **Online Store → Themes → Customize**.
6. Top dropdown → **Products → Default product**.
7. **Add section** and add them in this recommended order:

```
[ your existing image gallery + buy box ]   <- keep as-is
Pro Product Details      (features, trust, specs, FAQ)
Product Reviews          (Judge.me)
Sticky Add to Cart       (floats; position in the list doesn't matter)
```

8. Click each section to edit its text/blocks in the right panel. **Save**.
9. Preview. When happy: **Themes → … → Publish** to make it live.

> Safety net: because you edited a *duplicate*, your live store is untouched
> until you hit Publish. A bad change can never instantly break the store.

---

## Reviews — the legitimate way (you already have Judge.me)

The reviews block auto-fills once Judge.me is active. To populate it **legally**
(fabricated reviews violate India's IS 19000:2022 / Consumer Protection Act and
Judge.me's terms):

- **Import genuine Amazon reviews** for the same product using your installed
  *EZ Amazon Reviews Importer* / *K: Amazon Reviews* apps.
- Turn on **Judge.me → automatic review-request emails** to past buyers.
- Enable **photo reviews** in Judge.me for the Amazon-style look.

---

## "4K clarity" = your images, not code

No theme can sharpen blurry source photos. Upload product images:

- **2048 × 2048 px**, square, sharp, evenly lit, clean/white background.
- Shopify auto-generates crisp responsive sizes from these.
- Keep file sizes reasonable (compress to ~200–400 KB) so pages stay fast.

---

## Optional: automatic deploys via GitHub

To have future code changes apply to the store automatically:

1. Put this theme's files in the `nalanda-shopify-theme` GitHub repo
   (download your theme zip from Shopify and upload it, then add these sections).
2. Shopify admin → **Online Store → Themes → Add theme → Connect from GitHub**,
   pick the repo + branch.
3. From then on, every push to that branch syncs to the connected theme.

Note: GitHub sync covers **theme/design only** — products, prices, orders and
inventory are managed separately (Shopify admin or the Claude Shopify connector).
