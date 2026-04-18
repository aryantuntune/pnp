# PNP White-Label Design Spec
**Date:** 2026-04-12
**Project:** White-label SSMSPL ferry ticketing system for PNP Maritime Services Pvt. Ltd.

---

## 1. Overview

Replace all Suvarnadurga Shipping (SSMSPL) branding with PNP Maritime branding across the full-stack monorepo. Internal infrastructure naming (`ssmspl_` cookie prefixes, DB names, Docker names, bundle IDs) stays unchanged. Only user-visible content changes.

**Company being branded in:**
- Full name: PNP Maritime Services Pvt. Ltd.
- Short name: PNP Maritime
- CIN: U63090MH1999PTC121461
- Incorporated: 1999
- Service: AC catamaran ferry, Gateway of India (Mumbai) ↔ Mandwa Jetty
- Free connecting bus: Mandwa Jetty → Alibag ST Stand (included in fare)

---

## 2. Decisions Summary

| Decision | Choice |
|----------|--------|
| Vehicle/goods items | Keep all 21 in DB, set `is_active = FALSE` for items 1-10 (vehicles) and 13-16 (goods) |
| Route structure | 1 route only: Gateway of India ↔ Mandwa Jetty |
| Boat data | 3 placeholder catamarans seeded |
| Schedules | Seed from research data (7 departures each direction) |
| Logo replacement | Manual — client to provide PNP logo files |
| Domain placeholder | `pnp.example.com` / `api.pnp.example.com` |
| Internal naming | Unchanged (`ssmspl_` prefixes, DB names, cookies, bundle IDs) |
| About page | Mix: real PNP facts + `[CONFIRM WITH CLIENT]` markers |
| Test accounts | Seed admin + billing_operator accounts alongside superadmin |

---

## 3. Backend Seed Data (`backend/scripts/seed_data.sql`)

### 3.1 Branches — Replace all 14 with 2

| ID | Name | Address | Contact | Lat | Lng |
|----|------|---------|---------|-----|-----|
| 101 | GATEWAY OF INDIA | Apollo Bandar, Colaba, Mumbai 400001 | 022-22884535, 8591254683 | 18.9220 | 72.8347 |
| 102 | MANDWA JETTY | Mandwa Jetty, Alibaug, Raigad | 02141-237087, 8805401558 | 18.8105 | 72.8810 |

Operating hours: `sf_before: 06:00`, `sf_after: 21:00`

### 3.2 Routes — Replace 7 with 1

Route 1: GATEWAY OF INDIA (101) ↔ MANDWA JETTY (102), active

### 3.3 Schedules — Replace 155 entries with 14

**Gateway of India (101) → 7 departures:**
08:15, 10:15, 12:15, 14:15, 16:15, 18:30, 20:15

**Mandwa Jetty (102) → 7 departures:**
07:10, 09:05, 11:05, 13:05, 15:05, 17:05, 19:30

### 3.4 Boats — Replace 12 with 3 placeholders

- "Catamaran 1", "Catamaran 2", "Catamaran 3"

### 3.5 Items — Rename passengers, deactivate vehicles/goods

Keep all 21 IDs. Changes:
- Item 11: rename to "PASSENGER - MAIN DECK" (non-AC), `is_active = TRUE`
- Item 12: rename to "PASSENGER - AC DECK", `is_active = TRUE`
- Items 1-10 (vehicles): `is_active = FALSE`
- Items 13-16 (goods/livestock): `is_active = FALSE`
- Items 17-21 (tourist/passes/special): keep unchanged, `[CONFIRM WITH CLIENT]`

### 3.6 Item Rates — Route 1 only

- Item 11 (Main Deck): Rs. 285 (levy 0, rate 285)
- Item 12 (AC Deck): Rs. 325 (levy 0, rate 325) `[CONFIRM WITH CLIENT]`
- Items 17-21: Rs. 0 placeholder `[CONFIRM WITH CLIENT]`
- All vehicle/goods rates: Rs. 0 (deactivated items)

### 3.7 Company Record

```
name:        PNP Maritime Services Pvt. Ltd.
short_name:  PNP Maritime
reg_address: A-5, 18 Ionic, Arthur Bunder Road, Colaba, Mumbai MH-400005
contact:     022-22884535
email:       pnpipl11@gmail.com
gst_no:      [CONFIRM WITH CLIENT]
pan_no:      [CONFIRM WITH CLIENT]
cin_no:      U63090MH1999PTC121461
```

### 3.8 Users — Seed 3 test accounts (all Password@123)

| Username | Email | Role |
|----------|-------|------|
| superadmin | superadmin@ssmspl.com | SUPER_ADMIN (unchanged, internal) |
| admin | admin@pnp.example.com | ADMIN |
| billing | billing@pnp.example.com | BILLING_OPERATOR |

---

## 4. Backend Config (`backend/app/config.py`)

| Field | Old | New |
|-------|-----|-----|
| `APP_NAME` | "SSMSPL" | "PNP" |
| `SMTP_FROM_EMAIL` | noreply@ssmspl.com | noreply@pnp.example.com |
| `CONTACT_FORM_RECIPIENT` | ssmsdapoli@rediffmail.com | pnpipl11@gmail.com |

---

## 5. Frontend — Public Pages

### 5.1 `frontend/src/app/layout.tsx`
- title: `"PNP Maritime Services - Ferry Ticketing | Gateway of India to Mandwa"`
- description: `"Book catamaran ferry tickets from Gateway of India to Mandwa Jetty. AC and Main Deck seating. Includes free bus to Alibag."`
- metadataBase: `https://pnp.example.com`
- `appleWebApp.title`: `"PNP Ferry"`

### 5.2 `frontend/src/components/public/Header.tsx`
- Logo alt: `"PNP Maritime Services"`
- Brand line 1: `"PNP Maritime"`, line 2: `"Catamaran Ferry Service"`
- Top bar phone: `022-22884535`
- Top bar email: `pnpipl11@gmail.com`
- Operating hours: `"Operating: 8:15 AM - 8:15 PM (Daily)"`
- Remove "Houseboat Booking" link entirely

### 5.3 `frontend/src/components/public/Footer.tsx`
- Brand line 1: `"PNP Maritime"`, line 2: `"Catamaran & Ferry"`
- Tagline: `"Gateway to Mandwa since 1999. The fastest way to Alibag."`
- Contact bar block 1: "Gateway Office" — 022-22884535 / 8591254683
- Contact bar block 2: "Mandwa & Alibag Office" — 02141-237087 / 8805401558
- Ferry Routes list: `"Gateway of India – Mandwa Jetty"`
- Footer email: `pnpipl11@gmail.com`
- Copyright: `"© 2026 PNP Maritime Services Pvt. Ltd."`

### 5.4 `frontend/src/app/(public)/page.tsx` (Home)
- Hero badge: `"Mumbai's Premier Catamaran Service"`
- Hero subtext: `"Experience fast catamaran travel from Gateway of India to Mandwa Jetty. AC and non-AC seating. Includes free bus to Alibag."`
- Routes section: single card — `"Gateway of India – Mandwa Jetty"`, slug: `"gateway-mandwa"`
- "Our Other Services": replace 3 SSMSPL-specific services with:
  - Cruise/charter service `[CONFIRM WITH CLIENT]`
  - Port operations at Dharamtar `[CONFIRM WITH CLIENT]`
- "Why Choose Us" bullets:
  - Replace "Vehicle Transport" → `"AC Catamaran"`
  - Replace "Since 2003" → `"Since 1999"`
- Stats: `"25+"` years, `"1"` route, `"350+"` passengers/vessel, `"1M+"` passengers served
- About section heading: `"About PNP Maritime"`
- About section copy: PNP-specific content (Gateway-Mandwa service, catamaran, 1999)
- About section badges: `"350+ Capacity"`, `"1 Active Route"`, `"Daily Service"`

### 5.5 `frontend/src/app/(public)/about/page.tsx`
- Banner subtitle: `"Gateway to Alibag — Catamaran Ferry Since 1999"`
- `ferryRoutes` array: `["Gateway of India – Mandwa Jetty (incl. free bus to Alibag)"]`
- Stats: `{ "25+", "YEARS OF SERVICE" }`, `{ "1", "FERRY ROUTES" }`, `{ "[CONFIRM]", "EMPLOYEES" }`, `{ "1M+", "PASSENGERS SERVED" }`
- "Who We Are" heading: `"PNP Maritime Services Pvt. Ltd."`
- "Who We Are" copy: PNP description from research
- "Our Story" content: PNP history (incorporated 1999, Patil family, Gateway-Mandwa route, only AC catamaran operator) — sentences marked `[CONFIRM WITH CLIENT]` for unverified details
- Contact bar: Gateway Office + Mandwa/Alibag Office + pnpipl11@gmail.com
- Remove second email (y.mokal@rediffmail.com)

### 5.6 `frontend/src/app/(public)/route/[slug]/page.tsx`
- Remove all 7 SSMSPL route entries
- Add single `"gateway-mandwa"` entry:
  - name: `"Gateway of India – Mandwa Jetty"`
  - subtitle: `"The fastest sea route from Mumbai to Alibag. ~45 min catamaran + free bus."`
  - about: 3-4 paragraphs about the PNP service, Gateway of India, Mandwa Jetty, Alibag connection
  - tourist: nearby Alibag attractions
  - contacts: Gateway Office + Mandwa Office
  - timetableImage / ratecardImage: `null` (client to provide)

### 5.7 `frontend/src/app/(public)/contact/page.tsx`
- Replace 7 route phone groups with 3 offices:
  - Gateway of India: 022-22884535, 022-22885220, +91 8591254683
  - Mandwa Jetty: 02141-237087, 02141-237464
  - Alibag Office: 02141-225403, +91 8805401558
- Map coordinates: Gateway of India (18.9220, 72.8347)
- Email: pnpipl11@gmail.com

---

## 6. Frontend — Customer Portal

### 6.1 `frontend/src/app/customer/login/page.tsx`
- Any "SSMSPL" heading → "PNP Maritime"

### 6.2 `frontend/src/app/customer/register/page.tsx`
- Any "SSMSPL" heading → "PNP Maritime"

### 6.3 `frontend/src/app/customer/forgot-password/page.tsx`
- Any "SSMSPL" heading → "PNP Maritime"

---

## 7. Frontend — Dashboard (Admin)

### 7.1 Dashboard layout/sidebar
- Any "SSMSPL" text → "PNP"
- Company name in header/sidebar → "PNP Maritime"

### 7.2 `frontend/public/manifest.json`
- `name`: `"PNP Maritime Ferry"`
- `short_name`: `"PNP Ferry"`

---

## 8. Logo Files (Manual — Cannot be automated)

You must obtain PNP logo from the client and overwrite these files:

| Path | Purpose |
|------|---------|
| `frontend/public/images/logos/logo.png` | Header logo |
| `frontend/public/images/logos/logo-white.png` | Footer logo (white variant) |
| `frontend/public/favicon-16x16.png` | Browser tab |
| `frontend/public/favicon-32x32.png` | Browser tab |
| `frontend/public/apple-touch-icon.png` | iOS home screen |
| `frontend/public/android-chrome-192x192.png` | Android |
| `frontend/public/android-chrome-512x512.png` | Android |
| `frontend/public/og-image.png` | Social media preview |
| `backend/logo.png` | PDF/report watermark |
| `backend/logo_qr_code.png` | QR code center icon |

---

## 9. Out of Scope (This Sprint)

- Internal naming (`ssmspl_` cookie names, DB names, Docker, bundle IDs) — unchanged by design
- Bus route (Mandwa → Alibag) — pending client confirmation
- Route images / timetable images / rate card images — client to provide
- Vehicle/goods item rates — deactivated, no rates needed
- Domain configuration — client to provide domain, replace `pnp.example.com`
- CCAvenue merchant credentials — client to provide
- SMTP credentials — client to provide
- Production deployment — separate task
