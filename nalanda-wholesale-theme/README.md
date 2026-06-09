# Nalanda Wholesale — B2B Shopify OS 2.0 Theme

A standalone wholesale/trade theme for **Nalanda Enterprises**, built on the
NALANDA X design system. Model: **open wholesale** (public trade prices, anyone
can browse and order in bulk).

## What's B2B-specific here
- **Public trade pricing** with **"/unit"** display.
- **MOQ** (minimum order qty) — per product via metafield `custom.moq`, else the
  theme default in Settings → Wholesale.
- **Tier / volume pricing table** on the PDP via metafield `custom.tier_prices`
  (a *list* of strings like `10|₹899`, `50|₹849`, `100|₹799`).
- **Quantity stepper** that enforces MOQ; product card "Add N to order".
- **WhatsApp bulk-quote** buttons (set number in Settings → Wholesale).
- **GST invoicing / dispatch** messaging, **Become a dealer** trade CTA.
- Wholesale homepage (`templates/index.json`): hero → trust → catalogue → brands
  → deals → dealer CTA.

## Set up (Theme Settings → Wholesale / B2B)
- `default_moq`, `show_per_unit`, `whatsapp`, `gstin`, `trade_note`.

## Per-product metafields (Settings → Custom data → Products)
| Namespace.key | Type | Example |
|---|---|---|
| `custom.moq` | Integer | `10` |
| `custom.tier_prices` | List of single-line text | `10|₹899` , `50|₹849` , `100|₹799` |

## Deploy
Upload as a **separate theme** (ideally a separate store / the `nalandawholesale`
domain): Online Store → Themes → Add theme → Upload zip → set logo, menus,
wholesale settings → Customize → Publish. Or connect via GitHub.

Everything else (SEO/schema, analytics hooks, animation engine, required
templates, accessibility) is inherited from the NALANDA X foundation.
