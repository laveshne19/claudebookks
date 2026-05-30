# BizWrap India — Going Live + App Install Guide

This is a **real Vite/React project**, not a static file. Host the project (not the bundle.html) so that adding products / changing animations = push an update, and the live site rebuilds automatically.

---

## A. The 15-minute path to live (recommended: Vercel)

### 1. Put the code on GitHub
- Create a free account at github.com → "New repository" → name it `bizwrap-india` → Private → Create.
- On the upload page, drag in **all files from this project folder** (the `bizwrap-site` contents: `src/`, `public/`, `package.json`, `index.html`, `vite.config.ts`, etc.). Commit.
  - (Or, if you use git locally: `git init && git add . && git commit -m "init" && git remote add origin <repo-url> && git push -u origin main`.)

### 2. Deploy on Vercel (free)
- Go to vercel.com → sign up with GitHub → "Add New Project" → import `bizwrap-india`.
- Vercel auto-detects Vite. Confirm:
  - Build Command: `pnpm build` (or `npm run build`)
  - Output Directory: `dist`
- Click **Deploy**. ~1 min later you get a live URL like `bizwrap-india.vercel.app`. Test it.

### 3. Connect your Squarespace domain
You bought the domain on Squarespace, but you're **not** using Squarespace's website builder — only its DNS. Point the domain at Vercel:

- In Vercel: Project → **Settings → Domains** → add `bizwrapindia.com` and `www.bizwrapindia.com`. Vercel shows you the exact DNS records to add (an `A` record for the root and a `CNAME` for `www`).
- In **Squarespace**: log in → **Settings → Domains** → click `bizwrapindia.com` → **DNS Settings** (or "Use a domain you own / advanced DNS").
  - Add the **A record** Vercel gave you for `@` (root) → value is usually `76.76.21.21`.
  - Add the **CNAME** for `www` → value `cname.vercel-dns.com`.
  - Remove any old/parking A or CNAME records that conflict.
- Save. DNS takes 10 min–48 hrs to propagate (usually under an hour). Vercel issues the **free SSL (https)** automatically once it sees the records.

That's it — `https://www.bizwrapindia.com` is live, on a global CDN, with auto-HTTPS.

> **Netlify is an equally good free alternative.** Same idea: connect GitHub, build `pnpm build`, publish `dist`, then add the domain and copy its DNS records into Squarespace. `netlify.toml` is already included.

---

## B. The "app" (PWA) — install on any device, no app store

The site is now an **installable Progressive Web App**. There is **no Play Store / App Store submission** and **no separate app to maintain** — it's the same site, installable. The "Install App" link is in the **top ribbon** and the nav.

What users do:
- **Android (Chrome) / Desktop (Chrome, Edge):** an "Install App" button appears → one tap → it lands on the home screen / desktop with the BizWrap gift-box icon, opens full-screen (no browser bars).
- **iPhone/iPad (Safari):** tapping "Install App" shows a 3-step guide (Share → Add to Home Screen → Add). Apple doesn't allow one-tap install; this is the only path on iOS and it's normal.

Because it's a PWA:
- It updates itself — when you push new products/animations, installed apps get the new version automatically (the service worker is set to network-first for pages).
- It works offline for already-viewed content (app shell + cached product images).

> Requirement: PWA install only works over **https**, which you get free once the domain is on Vercel/Netlify. It will not offer install on a plain http or local file.

---

## C. How you make changes later (products, animations)

The project is built so updates are easy and isolated:

**Add / update products** — the catalogue lives in `src/catalog.json`. Two options:
1. **Re-export from Shopify** (Products → Export → CSV), then regenerate `catalog.json` with the same parser logic used to build it (drop the CSV in, run the script, replace the file). Push to GitHub → site auto-rebuilds.
2. **Better, long-term:** wire the live Shopify Admin API (you have the Shopify connector) to sync products into the site automatically, so you never touch JSON. Ask me to build this when ready.

**Change animations / sections** — every part of the page is its own file in `src/sections/` (e.g. `Hero.tsx`, `Shop.tsx`, `Metal.tsx`). Edit the one you want; the rest is untouched. The gift-box intro is `src/components/brand/Intro.tsx`.

**To preview locally before pushing:** `pnpm install` then `pnpm dev` → opens at localhost.

**To publish:** push to GitHub. Vercel/Netlify rebuild and deploy automatically in ~1 minute. No manual file uploads, ever.

---

## D. What's still on you (not buildable from code)
- The live deploy + DNS records above (needs your Vercel/Squarespace logins).
- **Client logos** (Coca-Cola etc.) are placeholders with a visible disclaimer — replace with only genuine, authorised client logos before launch.
- Brand logos: use official partner/media-kit assets or distributor authorisation; don't scrape.
- This marketing front-end is separate from the earlier Next.js backend (admin, RFQ database, auth). When you want quotes/leads actually stored and an admin panel, we merge the two.
