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

## Tested
- ✅ 23/23 backend pytest cases (auth, customers, dashboards, reports, AI insights, role guards)
- ✅ All frontend pages render with seeded data
- ✅ AI insights endpoint successfully calls Claude Sonnet 4.5 and returns valid 8-key JSON, cached for 6 hours

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
