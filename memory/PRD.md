# Nalanda Enterprises — ERP & CRM SaaS

## Original Problem Statement
Build a production-ready internal ERP + CRM + Sales Force Automation + Accounts Management + AI Analytics SaaS for **Nalanda Enterprises** (Electronics & Gadget distribution — Boat, Fireboltt, Noise, Logitech, Amazon, Swiss Military, Mivi). Multi-platform (web + responsive PWA + future mobile), role-based, AI-powered customer intelligence, Zoho Books sync, GPS/route planning, premium corporate UI.

## Tech Stack (delivered)
- **Backend:** FastAPI + MongoDB (Motor async)
- **Frontend:** React 19 + Tailwind + shadcn/ui + Recharts + Lucide icons
- **AI:** Emergent Universal LLM Key → Claude Sonnet 4.5 via `emergentintegrations`
- **Auth:** JWT (httpOnly cookies + Bearer fallback) + bcrypt + role-based permissions

## Design System
Swiss / Neo-Tactical B2B — Signal Orange `#FF4D00` primary, always-dark obsidian sidebar, Cabinet Grotesk display, IBM Plex Sans body, JetBrains Mono for numeric. AI insights rendered as "monochrome terminal" amber cards (no purple AI slop). Light + dark mode.

## User Personas
1. **Super Admin** — full control (Nalanda owner) · `admin@nalanda.com / Admin@123`
2. **Admin** — most controls minus user deletion
3. **Manager** — supervises sales team, targets, schemes · `manager@nalanda.com / Manager@123`
4. **Sales Person** — own customers, visits, AI insights · `sales1/2/3@nalanda.com / Sales@123`
5. **Accounts** — recovery, GST, reconciliation · `accounts@nalanda.com / Accounts@123`

## Implemented (16 May 2026)
- ✅ JWT auth with httpOnly cookies + Bearer fallback + brute-force-aware lockout shape
- ✅ 5 roles + route guards (frontend + backend)
- ✅ Auto-seeded realistic data: 7 users, 30 customers across 15 Mumbai areas, ~227 invoices, payments, 6 brand schemes, monthly targets, tasks, notifications, visits
- ✅ **Sales Dashboard** — 5 KPIs (MTD, target, achievement %, collection %, overdue), sales trend area chart, aging bar chart, priority customer list, AI recommendation card, open tasks
- ✅ **Customers** — searchable table, risk badges, brand tags
- ✅ **Customer 360** — sticky profile, call/SMS actions, 6 AI insight cards (Executive Summary, Credit Risk, Pay Behavior, Next Order Prediction, Recovery Approach, Pitch Points, Upsell, Best Visit Time), tabs: Invoices / Payments / Visits / Statement
- ✅ **Sales** — target progress, collection progress, brand split donut, 6-month sales vs collection bars, live schemes grid
- ✅ **Accounts** — KPIs, tabbed Overdue/Partial/Unpaid invoice tables, daily checklist, GST snapshot
- ✅ **Schemes** — full grid with progress bars and rewards
- ✅ **Route Map** — OpenStreetMap iframe + AI-prioritised stop list
- ✅ **Reports** — 12-month trend, aging, brand performance table with share bars, productivity leaderboard
- ✅ **Admin Panel** — 7 KPIs, leaderboard, Zoho sync trigger, users table with Add User dialog
- ✅ **Notifications** — type-coded list with unread indicators, mark-as-read
- ✅ Light/Dark theme toggle, persisted to localStorage

## Round 4 — Historical Excel Import LIVE (16 May 2026)
- ✅ **Real Nalanda data imported**: 5 salespeople (Rohit, Sarabjeet, Navneet, Davinder, Atinder)
- ✅ **299 real customers** from FY 2025-26 with auto-detected brand preferences
- ✅ **2,067 sales orders / 7,121 line items** ingested via `/app/backend/excel_importer.py`
- ✅ **₹9.54 Crore historical sales** captured · Top brands: Amazon ₹3.31Cr, Boat ₹2.95Cr, Logitech ₹1.29Cr, Swiss Military ₹46L, Fireboltt ₹43L, Noise ₹38L
- ✅ Brand auto-detection across Boat / Fireboltt / Noise / Logitech / Amazon / Swiss Military / Mivi / Toreto / Portronics / Ambrane / Syska / JBL / Samsung
- ✅ Idempotent re-runs · `POST /api/import/historical?force=false`
- ✅ Dashboard MTD/brand-split now falls back gracefully to last-90 / all-time when current month is empty
- ✅ Claude AI now produces insights grounded in real data: "Raju Traders is a high-value customer (₹5.77L lifetime) with excellent payment discipline—69% Boat preference"

## Round 3 — Zoho Live Engine + Capacitor Wrapper (16 May 2026)
- ✅ **Zoho Books sync engine** (`/app/backend/zoho_sync.py`) — auto-detects region (.in/.com/.eu/.com.au/.jp) and Organization ID; pulls customers, invoices, payments, credit notes; preserves local fields (assigned_to, lat/lng, brand_preferences); idempotent via `zoho_*_id`
- ✅ **30-min scheduler** now calls Zoho when configured, else local aggregate refresh
- ✅ **Endpoints**: `POST /api/sync/zoho`, `GET /api/sync/zoho/status`, `POST /api/sync/zoho/detect`, `GET /api/sync/logs`
- ✅ **Admin UI** Zoho card shows live status (credentials present, region, org, schedule) + last sync runs
- ✅ **Capacitor mobile wrapper** scaffolded at `/app/mobile/` — `capacitor.config.json`, `package.json` with `@capacitor-community/background-geolocation`, build scripts, `locationBootstrap.js`, and a complete `README.md` with build instructions for Android Studio + Xcode
- ⏳ **Zoho refresh token rejected** (`invalid_code` on .in region) — user's token appears to be either an authorization code (one-time) or has wrong scope. Step-by-step regeneration guide at `/app/memory/zoho_setup.md` — once a valid `ZohoBooks.fullaccess.all` refresh token is supplied, the live sync activates instantly.
- ✅ **Granular permissions** per user (modules, brands, view_scope, customer_visibility, can_edit/create/export/manage_users) — fully editable by admin via Permissions dialog
- ✅ **Viewer role** for external brand partners — `boat@nalanda.com / Boat@123` sees ONLY daily Boat sales totals, no customer names, no other modules
- ✅ **Silent GPS attendance** — `useSilentLocationPing` posts location every 5 min while app open; no UI/notification; auto check-in/out; admin sees attendance roll-call + live locations
- ✅ **AI Route Planner** (`/api/ai/route-plan`) — Claude Sonnet 4.5 ranks customers by overdue × opportunity × area cluster using LIVE data, returns ordered stops with reason/objective/suggested time
- ✅ **AI Performance Coach** (`/api/ai/performance`) — Claude analyses LIVE 30-day metrics → rating + strengths + gaps + concrete next-actions + predicted MTD-end %
- ✅ **PWA** — manifest.json + service-worker + icons → installable on iOS Safari & Android Chrome (Add to Home Screen)
- ✅ **Hourly scheduler** (APScheduler) — re-aggregates customer outstanding/overdue every 60 min so dashboard stays live even before Zoho is wired
- ✅ **Permission-aware sidebar** — items filtered by `effective_permissions.modules`

## Tested
- ✅ 48/48 backend pytest cases (23 iter1 + 25 round2)
- ✅ All frontend flows verified including Boat viewer (only Dashboard visible, totals-only view), AI Route map+stops, AI Performance card, Admin permissions dialog, Attendance panels
- ✅ Claude Sonnet 4.5 verified producing live, data-grounded text (route reasoning, performance coaching, customer insights)

## Backlog (P1/P2 — Phase 2)
- **P1** Live Zoho Books OAuth sync engine (currently stub — endpoint ready, awaits `ZOHO_CLIENT_ID/SECRET/REFRESH_TOKEN/ORG_ID` in .env)
- **P1** Historical Excel/CSV import for Zoho previous-year data (AI training)
- **P1** GPS attendance + silent location tracking (mobile)
- **P2** WhatsApp message templates + Twilio SMS integration
- **P2** Push notifications (FCM)
- **P2** Export to PDF / Excel / CSV for reports
- **P2** Mobile native app (React Native shell consuming same API)
- **P2** Background scheduler (APScheduler) running Zoho sync every 30 min once keys are added
- **P2** Audit logs + device management for sessions

## Next Tasks
1. Collect Zoho Books credentials from user, wire `zoho_sync.py` module
2. Add Excel/CSV upload for historical data
3. Add Stripe billing (if Nalanda decides to white-label this to other distributors)
