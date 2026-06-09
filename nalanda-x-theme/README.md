# NALANDA X — Flagship Shopify OS 2.0 Theme

> India's Premium Gadget Destination. *Apple meets Tesla meets Nothing meets Dyson.*

A modular, performance-first Shopify Online Store 2.0 theme for **Nalanda Enterprises**.
Built with a token-driven design system, a lightweight 60fps animation engine, and a
full SEO/structured-data framework.

---

## Build phases (honest status)

This repo is delivered in phases. **Phase 1 (in this commit) is real, deployable code** —
not mockups.

| Phase | Scope | Status |
|---|---|---|
| **1 — Foundation** | Design system, animation engine, layout, header + mega-menu, immersive hero, product card, featured collection, brand showcase, value props, footer, world-class PDP, SEO/schema framework, homepage + product templates | ✅ In this commit |
| **2 — Catalog** | Collection page w/ animated filters + infinite scroll, smart search results, cart drawer, predictive search | ⏳ Next |
| **3 — Conversion** | Comparison, wishlist, recently-viewed, FBT bundles, urgency/social-proof, recently-purchased toasts | ⏳ Roadmap |
| **4 — Content** | Blog/Tech Insights, Instagram feed, corporate gifting, metaobject brand pages | ⏳ Roadmap |
| **5 — Required stubs** | Remaining mandatory templates (blog, article, page, 404, password, gift_card, list-collections) for a clean upload | ⚠️ Generate before first upload |

> A Shopify theme needs all mandatory templates present to upload cleanly. Phase 1 ships
> `index`, `product`, `collection`, `cart`. Ask me to generate the Phase 5 stubs and I'll
> add them so the ZIP validates.

---

## Folder structure

```
nalanda-x-theme/
├── assets/
│   ├── nalanda.css        # Design system + all component styles (token-driven)
│   └── nalanda.js         # Animation engine, interactions, cart, search
├── config/
│   ├── settings_schema.json   # Theme editor controls (colors, type, layout)
│   └── settings_data.json     # Default preset
├── layout/
│   └── theme.liquid       # Shell: head, SEO, analytics hooks, skip-link, a11y
├── locales/
│   └── en.default.json    # Strings
├── sections/
│   ├── header.liquid          # Sticky glass header + animated mega menu
│   ├── hero.liquid            # Parallax immersive hero
│   ├── featured-collection.liquid
│   ├── brand-showcase.liquid  # Boat, Noise, Fire-Boltt … marquee
│   ├── value-props.liquid     # Why Nalanda / trust row
│   ├── footer.liquid
│   ├── main-product.liquid    # Flagship PDP
│   └── main-collection.liquid
├── snippets/
│   ├── meta-tags.liquid       # Dynamic title/description/canonical/OG/Twitter
│   ├── structured-data.liquid # Org + Product + Breadcrumb + FAQ JSON-LD
│   ├── product-card.liquid    # Floating, magnetic, hover-zoom card
│   └── cart-drawer.liquid
└── templates/
    ├── index.json
    ├── product.json
    ├── collection.json
    └── cart.liquid
```

## Design system (tokens in `config/settings_schema.json` → CSS vars in `nalanda.css`)

- **Color:** ink (#0A0A0B), surface, glass tints, electric accent (configurable), gradient pairs.
- **Type:** large display scale, fluid `clamp()` sizing, tight tracking on headings.
- **Space:** 4px base, luxury section rhythm (`--space-section`).
- **Depth:** layered shadow tokens + glassmorphism (`backdrop-filter`) utilities.
- **Motion:** `--ease-out-expo`, reduced-motion safe; all animations GPU-composited (transform/opacity only).

## Performance principles

- Two assets only (1 CSS, 1 JS), deferred JS, `IntersectionObserver`-driven reveals.
- `image_url` responsive `srcset`, `loading="lazy"`, `width/height` to kill CLS.
- No render-blocking webfonts (font-display swap via Shopify `font_face`).
- Animations limited to `transform`/`opacity` for 60fps; honors `prefers-reduced-motion`.

## SEO & analytics

- `meta-tags.liquid` outputs canonical, OG, Twitter, robots, paginated rel.
- `structured-data.liquid` emits Organization, Product (with `offers`, `aggregateRating`),
  BreadcrumbList, FAQPage JSON-LD — Merchant-Center / Rich-Results ready.
- Analytics hooks in `theme.liquid` for GTM, GA4, Meta Pixel, Microsoft Clarity (paste IDs in theme settings).

## Deploy

1. Move this folder's **contents** to the root of your `nalanda-shopify-theme` repo.
2. Shopify admin → Online Store → Themes → **Add theme → Connect from GitHub** → pick the repo/branch.
3. Preview, then **Publish**. (Generate Phase 5 stubs first for a clean validation.)
