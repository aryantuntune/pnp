# PNP White-Label Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** White-label the SSMSPL ferry ticketing system for PNP Maritime Services Pvt. Ltd., replacing all user-visible Suvarnadurga/SSMSPL branding with PNP Maritime branding.

**Architecture:** Content-only replacement — no logic changes. Internal naming (`ssmspl_` cookie keys, DB names, localStorage keys, CSS data attributes, bundle IDs) stays unchanged. All user-visible text, contact info, route data, and seed data is replaced.

**Tech Stack:** FastAPI (Python 3.12), Next.js 16 / React 19 / TypeScript, PostgreSQL 16

**Spec:** `docs/superpowers/specs/2026-04-12-pnp-white-label-design.md`

---

## File Map

| File | Change Type |
|------|-------------|
| `backend/scripts/seed_data.sql` | Full rewrite — new branches, routes, schedules, boats, items, rates, company, users |
| `backend/app/config.py` | String: APP_NAME, SMTP_FROM_EMAIL, CONTACT_FORM_RECIPIENT |
| `backend/app/main.py` | String: description, contact email |
| `backend/app/services/email_service.py` | String: company name in 4 HTML templates |
| `backend/app/services/daily_report_service.py` | String: filename, subject, HTML footer |
| `backend/app/services/ccavenue_service.py` | String: order ID prefix |
| `frontend/src/components/public/Header.tsx` | String: company name, phone, email, hours |
| `frontend/src/components/public/Footer.tsx` | String: company name, contacts, routes list, copyright |
| `frontend/src/app/layout.tsx` | String: title, description, metadataBase, appleWebApp title |
| `frontend/public/manifest.json` | String: name, short_name, description |
| `frontend/src/app/(public)/page.tsx` | Partial rewrite: ROUTES array, SERVICES array, stats, about section |
| `frontend/src/app/(public)/about/page.tsx` | Partial rewrite: company copy, routes list, stats, contacts |
| `frontend/src/app/(public)/route/[slug]/page.tsx` | Full rewrite of ROUTE_DATA object |
| `frontend/src/app/(public)/contact/page.tsx` | String: phone numbers, office names |
| `frontend/src/app/customer/login/page.tsx` | String: SSMSPL → PNP Maritime (3 occurrences) |
| `frontend/src/app/customer/register/page.tsx` | String: SSMSPL → PNP Maritime (3 occurrences) |
| `frontend/src/app/customer/forgot-password/page.tsx` | String: SSMSPL → PNP Maritime (3 occurrences) |
| `frontend/src/app/customer/reset-password/page.tsx` | String: SSMSPL → PNP Maritime (3 occurrences) |
| `frontend/src/app/customer/verify-email/page.tsx` | String: SSMSPL → PNP Maritime (3 occurrences) |
| `frontend/src/components/customer/CustomerLayout.tsx` | String: company name, copyright |
| `frontend/src/components/dashboard/AppSidebar.tsx` | String: SSMSPL → PNP |
| `frontend/src/components/Navbar.tsx` | String: SSMSPL → PNP |
| `frontend/src/app/dashboard/branches/page.tsx` | String: SSMSPL → PNP in PDF/HTML exports |
| `frontend/src/app/dashboard/ticketing/page.tsx` | String: certificate link text only (not file path) |
| `frontend/src/app/dashboard/settings/components/backups-tab.tsx` | String: placeholder email |
| `frontend/src/app/dashboard/settings/components/notifications-tab.tsx` | String: placeholder email |
| `frontend/src/app/dashboard/users/page.tsx` | String: placeholder email |
| `frontend/src/lib/print-receipt.ts` | String: website URL in receipt footer |

---

## Task 1: Rewrite seed_data.sql for PNP

**Files:**
- Modify: `backend/scripts/seed_data.sql`

- [ ] **Step 1: Replace the entire seed_data.sql with PNP data**

Replace the full contents of `backend/scripts/seed_data.sql` with:

```sql
-- ============================================================
-- PNP Maritime Services Pvt. Ltd. — Seed Data
-- ============================================================
-- Prerequisites: Run ddl.sql first on a clean database.
-- Default password for all seed users: Password@123
-- IMPORTANT: Change passwords before deploying to production!
-- ============================================================

BEGIN;

-- ============================================================
-- 1. BRANCHES (2)
-- ============================================================
INSERT INTO branches (id, name, address, contact_nos, latitude, longitude, sf_after, sf_before, last_ticket_no, last_booking_no, is_active)
VALUES
    (101, 'GATEWAY OF INDIA', 'Apollo Bandar, Colaba, Mumbai 400001',      '022-22884535, 8591254683', 18.922000, 72.834700, '21:00:00', '06:00:00', 0, 0, TRUE),
    (102, 'MANDWA JETTY',     'Mandwa Jetty, Alibaug, Raigad 402201',      '02141-237087, 8805401558', 18.810500, 72.881000, '21:00:00', '06:00:00', 0, 0, TRUE)
ON CONFLICT (name) DO UPDATE SET
    address     = EXCLUDED.address,
    contact_nos = EXCLUDED.contact_nos,
    latitude    = EXCLUDED.latitude,
    longitude   = EXCLUDED.longitude,
    sf_after    = EXCLUDED.sf_after,
    sf_before   = EXCLUDED.sf_before,
    is_active   = EXCLUDED.is_active,
    updated_at  = NOW();

-- ============================================================
-- 2. ROUTES (1)
-- ============================================================
INSERT INTO routes (id, branch_id_one, branch_id_two, is_active)
VALUES
    (1, 101, 102, TRUE)   -- GATEWAY OF INDIA <-> MANDWA JETTY
ON CONFLICT (id) DO UPDATE SET
    branch_id_one = EXCLUDED.branch_id_one,
    branch_id_two = EXCLUDED.branch_id_two,
    is_active     = EXCLUDED.is_active,
    updated_at    = NOW();

-- ============================================================
-- 3. USERS (3 test accounts — all Password@123)
-- ============================================================
INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_verified)
VALUES
    (uuid_generate_v4(), 'superadmin@ssmspl.com',       'superadmin', 'Super Administrator',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'SUPER_ADMIN',      TRUE, TRUE),
    (uuid_generate_v4(), 'admin@pnp.example.com',       'admin',      'PNP Admin',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'ADMIN',            TRUE, TRUE),
    (uuid_generate_v4(), 'billing@pnp.example.com',     'billing',    'PNP Billing Operator',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- 4. BOATS (3 placeholders)
-- ============================================================
INSERT INTO boats (id, name, no, is_active)
VALUES
    (1, 'Catamaran 1', 'PNP-CAT-001', TRUE),
    (2, 'Catamaran 2', 'PNP-CAT-002', TRUE),
    (3, 'Catamaran 3', 'PNP-CAT-003', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================================
-- 5. ITEMS (21 — vehicles 1-10 and goods 13-16 deactivated)
-- ============================================================
INSERT INTO items (id, name, short_name, online_visiblity, is_vehicle, is_active)
VALUES
    -- Vehicles (deactivated — PNP is passenger-only catamaran)
    (1,  'CYCLE',                                         'CYCLE',                FALSE, TRUE,  FALSE),
    (2,  'MOTOR CYCLE WITH DRIVER',                       'MOTORCYCLE W/ DRIVER', FALSE, TRUE,  FALSE),
    (3,  'EMPTY 3 WHLR RICKSHAW',                        '3 WHLR RICKSHAW',      FALSE, TRUE,  FALSE),
    (4,  'MAGIC/IRIS/CAR',                               'MAGIC/IRIS/CAR',       FALSE, TRUE,  FALSE),
    (5,  'LUX CAR 5 ST/SUMO/SCORPIO/TAVERA 7 ST',       'LUX CAR/SUMO',         FALSE, TRUE,  FALSE),
    (6,  'AMBULANCE',                                     'AMBULANCE',            FALSE, TRUE,  FALSE),
    (7,  'T.T/407/709/18 & 21 ST BUS',                  'TT/407/709/BUS',       FALSE, TRUE,  FALSE),
    (8,  'BUS/TRUCK/TANKER',                             'BUS/TRUCK/TANKER',     FALSE, TRUE,  FALSE),
    (9,  'TRUCK 10 WHLR/JCB',                           'TRUCK 10 WHLR/JCB',   FALSE, TRUE,  FALSE),
    (10, 'TRACTOR WITH TROLLY',                          'TRACTOR W/ TROLLY',    FALSE, TRUE,  FALSE),
    -- Passengers (renamed for PNP deck types)
    (11, 'PASSENGER - MAIN DECK',                        'MAIN DECK',            TRUE,  FALSE, TRUE),
    (12, 'PASSENGER - AC DECK',                          'AC DECK',              TRUE,  FALSE, TRUE),
    -- Goods / livestock / luggage (deactivated)
    (13, 'GOODS PER HALF TON',                          'GOODS/HALF TON',       FALSE, FALSE, FALSE),
    (14, 'PASS LUG ABV 20KG PER KG',                   'LUGGAGE ABV 20KG/KG',  FALSE, FALSE, FALSE),
    (15, 'DOG/GOATS/SHEEP & FISH/CHICKEN/BIRDS/FRUITS', 'ANIMALS & GOODS',      FALSE, FALSE, FALSE),
    (16, 'COWS/BUFFELLOW (PER NO)',                     'COWS/BUFFALO',         FALSE, FALSE, FALSE),
    -- Tourist / passes / special (CONFIRM RATES WITH CLIENT before going live)
    (17, 'TOURIST (FOR 1 HOUR)',                        'TOURIST 1HR',          TRUE,  FALSE, TRUE),
    (18, 'MONTH PASS STUDENT UPTO 7TH',                 'STDNT PASS UPTO 7TH',  FALSE, FALSE, TRUE),
    (19, 'MONTH PASS STUDENT ABOVE XTH',                'STDNT PASS ABOVE XTH', FALSE, FALSE, TRUE),
    (20, 'MONTH PASS PASSENGER',                        'PASSENGER MONTH PASS', FALSE, FALSE, TRUE),
    (21, 'SPECIAL FERRY',                               'SPECIAL FERRY',         FALSE, FALSE, TRUE)
ON CONFLICT (id) DO UPDATE SET
    name              = EXCLUDED.name,
    short_name        = EXCLUDED.short_name,
    online_visiblity  = EXCLUDED.online_visiblity,
    is_vehicle        = EXCLUDED.is_vehicle,
    is_active         = EXCLUDED.is_active,
    updated_at        = NOW();

-- ============================================================
-- 6. PAYMENT MODES (unchanged)
-- ============================================================
INSERT INTO payment_modes (id, description, is_active, show_at_pos)
VALUES
    (1, 'Cash',   TRUE,  TRUE),
    (2, 'UPI',    TRUE,  TRUE),
    (3, 'Card',   TRUE,  TRUE),
    (4, 'Online', TRUE,  FALSE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 7. FERRY SCHEDULES — PNP timetable (14 departures)
--    Source: https://www.gatewaypass.in/pnp-ferry-timings
-- ============================================================
INSERT INTO ferry_schedules (id, branch_id, departure)
VALUES
    -- Gateway of India (101) → Mandwa — 7 departures
    (1,  101, '08:15'),
    (2,  101, '10:15'),
    (3,  101, '12:15'),
    (4,  101, '14:15'),
    (5,  101, '16:15'),
    (6,  101, '18:30'),
    (7,  101, '20:15'),
    -- Mandwa Jetty (102) → Gateway — 7 departures
    (8,  102, '07:10'),
    (9,  102, '09:05'),
    (10, 102, '11:05'),
    (11, 102, '13:05'),
    (12, 102, '15:05'),
    (13, 102, '17:05'),
    (14, 102, '19:30')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 8. ITEM RATES — Route 1: GATEWAY ↔ MANDWA
--    CONFIRM passenger rates with client before going live.
--    Vehicles/goods deactivated (is_active=FALSE).
-- ============================================================
INSERT INTO item_rates (levy, rate, item_id, route_id, is_active)
VALUES
    -- Deactivated vehicle items
    (0.00,   0.00,  1, 1, FALSE),
    (0.00,   0.00,  2, 1, FALSE),
    (0.00,   0.00,  3, 1, FALSE),
    (0.00,   0.00,  4, 1, FALSE),
    (0.00,   0.00,  5, 1, FALSE),
    (0.00,   0.00,  6, 1, FALSE),
    (0.00,   0.00,  7, 1, FALSE),
    (0.00,   0.00,  8, 1, FALSE),
    (0.00,   0.00,  9, 1, FALSE),
    (0.00,   0.00, 10, 1, FALSE),
    -- Active passenger items (CONFIRM FINAL RATES WITH CLIENT)
    (0.00, 285.00, 11, 1, TRUE),   -- PASSENGER - MAIN DECK
    (0.00, 325.00, 12, 1, TRUE),   -- PASSENGER - AC DECK
    -- Deactivated goods items
    (0.00,   0.00, 13, 1, FALSE),
    (0.00,   0.00, 14, 1, FALSE),
    (0.00,   0.00, 15, 1, FALSE),
    (0.00,   0.00, 16, 1, FALSE),
    -- Tourist/pass items — rates TBD, set to 0 (CONFIRM WITH CLIENT)
    (0.00,   0.00, 17, 1, TRUE),
    (0.00,   0.00, 18, 1, TRUE),
    (0.00,   0.00, 19, 1, TRUE),
    (0.00,   0.00, 20, 1, TRUE),
    (0.00,   0.00, 21, 1, TRUE)
ON CONFLICT (item_id, route_id) DO UPDATE SET
    rate = EXCLUDED.rate, levy = EXCLUDED.levy, is_active = EXCLUDED.is_active, updated_at = NOW();

-- ============================================================
-- 9. COMPANY
-- ============================================================
INSERT INTO company (id, name, short_name, reg_address, gst_no, pan_no, tan_no, cin_no, contact, email, sf_item_id, updated_at)
VALUES
    (1,
     'PNP Maritime Services Pvt. Ltd.',
     'PNP Maritime',
     'A-5, 18 Ionic, Arthur Bunder Road, Colaba, Mumbai MH-400005',
     'N/A',
     'N/A',
     'N/A',
     'U63090MH1999PTC121461',
     '022-22884535',
     'pnpipl11@gmail.com',
     21,
     NOW()
    )
ON CONFLICT (id) DO UPDATE SET
    name        = EXCLUDED.name,
    short_name  = EXCLUDED.short_name,
    reg_address = EXCLUDED.reg_address,
    cin_no      = EXCLUDED.cin_no,
    contact     = EXCLUDED.contact,
    email       = EXCLUDED.email,
    sf_item_id  = EXCLUDED.sf_item_id,
    updated_at  = NOW();

COMMIT;

-- ============================================================
-- VERIFICATION
-- ============================================================
SELECT 'Branches'       AS entity, COUNT(*) AS total FROM branches;
SELECT 'Routes'         AS entity, COUNT(*) AS total FROM routes;
SELECT 'Users'          AS entity, COUNT(*) AS total FROM users;
SELECT 'Boats'          AS entity, COUNT(*) AS total FROM boats;
SELECT 'Items'          AS entity, COUNT(*) AS total FROM items;
SELECT 'Active Items'   AS entity, COUNT(*) AS total FROM items WHERE is_active = TRUE;
SELECT 'Payment Modes'  AS entity, COUNT(*) AS total FROM payment_modes;
SELECT 'Ferry Schedules'AS entity, COUNT(*) AS total FROM ferry_schedules;
SELECT 'Item Rates'     AS entity, COUNT(*) AS total FROM item_rates;
SELECT r.id, b1.name AS branch_one, b2.name AS branch_two
  FROM routes r
  JOIN branches b1 ON b1.id = r.branch_id_one
  JOIN branches b2 ON b2.id = r.branch_id_two
  ORDER BY r.id;
```

- [ ] **Step 2: Verify the new seed file has no SSMSPL/Suvarnadurga references**

```bash
grep -n "SSMSPL\|Suvarnadurga\|Dabhol\|Dhopave\|carferry" backend/scripts/seed_data.sql
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/seed_data.sql
git commit -m "feat: replace SSMSPL seed data with PNP Maritime branches, routes, schedules, and company record"
```

---

## Task 2: Backend Config and API Description

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update config.py — APP_NAME and emails**

In `backend/app/config.py`, make these 3 changes:

Change 1:
```python
# old
    APP_NAME: str = "SSMSPL"
# new
    APP_NAME: str = "PNP"
```

Change 2:
```python
# old
    SMTP_FROM_EMAIL: str = "noreply@ssmspl.com"
# new
    SMTP_FROM_EMAIL: str = "noreply@pnp.example.com"
```

Change 3:
```python
# old
    CONTACT_FORM_RECIPIENT: str = "ssmsdapoli@rediffmail.com"
# new
    CONTACT_FORM_RECIPIENT: str = "pnpipl11@gmail.com"
```

- [ ] **Step 2: Update main.py — API description and contact**

In `backend/app/main.py`, make these 2 changes:

Change 1 (description string):
```python
# old
        "## SSMSPL Ferry Boat Ticketing System\n\n"
        "REST API for **Suvarnadurga Shipping & Marine Services Pvt. Ltd.**\n\n"
# new
        "## PNP Ferry Ticketing System\n\n"
        "REST API for **PNP Maritime Services Pvt. Ltd.**\n\n"
```

Change 2 (contact):
```python
# old
    contact={
        "name": "SSMSPL Engineering",
        "email": "engineering@ssmspl.com",
    },
# new
    contact={
        "name": "PNP Engineering",
        "email": "engineering@pnp.example.com",
    },
```

- [ ] **Step 3: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga\|ssmspl\.com\|ssmsdapoli" backend/app/config.py backend/app/main.py
```
Expected: no output

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/app/main.py
git commit -m "feat: update backend APP_NAME and emails to PNP Maritime"
```

---

## Task 3: Backend Email Service

**Files:**
- Modify: `backend/app/services/email_service.py`

- [ ] **Step 1: Replace all company name references in email templates**

In `backend/app/services/email_service.py`, make these changes (use replace_all where appropriate):

Change 1 — all 4 HTML template footers:
```python
# old (appears 4 times)
            Suvarnadurga Shipping &amp; Marine Services Pvt. Ltd.
# new
            PNP Maritime Services Pvt. Ltd.
```
Use `replace_all: true` for this one.

Change 2 — password reset email header subtitle:
```python
# old
            <p style="margin:8px 0 0;opacity:0.9;">SSMSPL Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Hello {user_name},</p>
            <p>We received a request to reset your password.
# new
            <p style="margin:8px 0 0;opacity:0.9;">PNP Maritime Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Hello {user_name},</p>
            <p>We received a request to reset your password.
```

Change 3 — OTP email header subtitle:
```python
# old
            <p style="margin:8px 0 0;opacity:0.9;">SSMSPL Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Hello {user_name},</p>
            <p>Use the following code to {purpose_text}:
# new
            <p style="margin:8px 0 0;opacity:0.9;">PNP Maritime Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Hello {user_name},</p>
            <p>Use the following code to {purpose_text}:
```

Change 4 — OTP email subject:
```python
# old
        msg["Subject"] = f"{subject} - SSMSPL Ferry Services"
# new
        msg["Subject"] = f"{subject} - PNP Maritime Ferry Services"
```

Change 5 — password reset email subject:
```python
# old
        msg["Subject"] = "Password Reset - SSMSPL Ferry Services"
# new
        msg["Subject"] = "Password Reset - PNP Maritime Ferry Services"
```

Change 6 — contact form header subtitle:
```python
# old
            <p style="margin:8px 0 0;opacity:0.9;">SSMSPL Website</p>
# new
            <p style="margin:8px 0 0;opacity:0.9;">PNP Maritime Website</p>
```

Change 7 — contact form footer:
```python
# old
            Sent from the SSMSPL website contact form
# new
            Sent from the PNP Maritime website contact form
```

Change 8 — booking confirmation header subtitle:
```python
# old
            <p style="margin:8px 0 0;opacity:0.9;">SSMSPL Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Dear Customer,</p>
# new
            <p style="margin:8px 0 0;opacity:0.9;">PNP Maritime Ferry Services</p>
        </div>
        <div style="padding:24px;background:#ffffff;">
            <p>Dear Customer,</p>
```

- [ ] **Step 2: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga" backend/app/services/email_service.py
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/email_service.py
git commit -m "feat: replace SSMSPL/Suvarnadurga branding in email templates with PNP Maritime"
```

---

## Task 4: Backend Daily Report and CCAvenue

**Files:**
- Modify: `backend/app/services/daily_report_service.py`
- Modify: `backend/app/services/ccavenue_service.py`

- [ ] **Step 1: Update daily_report_service.py**

Change 1 — PDF filename:
```python
# old
            filename = f"SSMSPL_Daily_Report_{report_date.strftime('%d_%m_%Y')}.pdf"
# new
            filename = f"PNP_Daily_Report_{report_date.strftime('%d_%m_%Y')}.pdf"
```

Change 2 — email subject:
```python
# old
                subject=f"SSMSPL Daily Report — {report_date.strftime('%d/%m/%Y')}",
# new
                subject=f"PNP Daily Report — {report_date.strftime('%d/%m/%Y')}",
```

Change 3 — email HTML header:
```python
# old
            <h1 style="margin:0;font-size:22px;">SSMSPL Daily Report</h1>
# new
            <h1 style="margin:0;font-size:22px;">PNP Daily Report</h1>
```

Change 4 — email HTML footer:
```python
# old
            Suvarnadurga Shipping &amp; Marine Services Pvt. Ltd.
# new
            PNP Maritime Services Pvt. Ltd.
```

- [ ] **Step 2: Update ccavenue_service.py — order ID prefix**

```python
# old
    return f"SSMSPL_{booking_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
# new
    return f"PNP_{booking_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
```

- [ ] **Step 3: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga" backend/app/services/daily_report_service.py backend/app/services/ccavenue_service.py
```
Expected: no output

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/daily_report_service.py backend/app/services/ccavenue_service.py
git commit -m "feat: update daily report and CCAvenue branding to PNP Maritime"
```

---

## Task 5: Frontend Header and Footer

**Files:**
- Modify: `frontend/src/components/public/Header.tsx`
- Modify: `frontend/src/components/public/Footer.tsx`

- [ ] **Step 1: Update Header.tsx**

Change 1 — top bar phone:
```tsx
// old
              +91 9767248900
// new
              022-22884535
```
Also update the `href`:
```tsx
// old
            <a href="tel:+919767248900"
// new
            <a href="tel:02222884535"
```

Change 2 — top bar email:
```tsx
// old
              ssmsdapoli@rediffmail.com
// new
              pnpipl11@gmail.com
```
Also update the `href`:
```tsx
// old
            <a href="mailto:ssmsdapoli@rediffmail.com"
// new
            <a href="mailto:pnpipl11@gmail.com"
```

Change 3 — operating hours:
```tsx
// old
            Operating: 6:00 AM - 10:00 PM (7 Days)
// new
            Operating: 8:15 AM - 8:15 PM (Daily)
```

Change 4 — logo alt text:
```tsx
// old
              alt="Suvarnadurga Shipping"
// new
              alt="PNP Maritime Services"
```

Change 5 — brand name line 1:
```tsx
// old
              <span className="font-bold text-[#0c3547] text-base group-hover:text-[#0891b2] transition-colors">Suvarnadurga</span>
// new
              <span className="font-bold text-[#0c3547] text-base group-hover:text-[#0891b2] transition-colors">PNP Maritime</span>
```

Change 6 — brand name line 2:
```tsx
// old
              <span className="text-xs text-amber-500">Shipping &amp; Marine Services</span>
// new
              <span className="text-xs text-amber-500">Catamaran Ferry Service</span>
```

Change 7 — remove Houseboat Booking link (both desktop and mobile, 2 occurrences):
```tsx
// old (desktop)
                <a
                  href="https://supriyahouseboat.bookingjini.in"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-amber-600 hover:text-amber-800 transition-colors"
                >
                  Houseboat Booking
                </a>
// new (delete this block entirely)
```

```tsx
// old (mobile)
                  <a
                    href="https://supriyahouseboat.bookingjini.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-center text-sm font-semibold text-amber-600"
                  >
                    Houseboat Booking
                  </a>
// new (delete this block entirely)
```

- [ ] **Step 2: Update Footer.tsx**

Change 1 — footer logo alt:
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — footer brand line 1:
```tsx
// old
                <span className="font-bold text-white text-base">Suvarnadurga</span>
// new
                <span className="font-bold text-white text-base">PNP Maritime</span>
```

Change 3 — footer brand line 2:
```tsx
// old
                <span className="text-xs text-gray-400">Shipping &amp; Marine</span>
// new
                <span className="text-xs text-gray-400">Catamaran &amp; Ferry</span>
```

Change 4 — footer tagline:
```tsx
// old
              Connecting Maharashtra&apos;s beautiful Konkan coast with reliable ferry services since 2003.
// new
              Gateway to Mandwa since 1999. The fastest way to Alibag.
```

Change 5 — contact bar block 1 (replace Dabhol Office with Gateway Office):
```tsx
// old
          <div className="text-center">
            <h4 className="font-bold text-white mb-3 text-lg">Dabhol Office</h4>
            <p className="text-white/90 text-sm">02348-248900</p>
            <p className="text-white/90 text-sm">+91 9767248900</p>
          </div>
// new
          <div className="text-center">
            <h4 className="font-bold text-white mb-3 text-lg">Gateway of India Office</h4>
            <p className="text-white/90 text-sm">022-22884535</p>
            <p className="text-white/90 text-sm">+91 8591254683</p>
          </div>
```

Change 6 — contact bar block 2 (replace Veshvi Office with Mandwa/Alibag Office):
```tsx
// old
          <div className="text-center">
            <h4 className="font-bold text-white mb-3 text-lg">Veshvi Office</h4>
            <p className="text-white/90 text-sm">02350-223300</p>
            <p className="text-white/90 text-sm">+91 8767980300</p>
          </div>
// new
          <div className="text-center">
            <h4 className="font-bold text-white mb-3 text-lg">Mandwa &amp; Alibag Office</h4>
            <p className="text-white/90 text-sm">02141-237087</p>
            <p className="text-white/90 text-sm">+91 8805401558</p>
          </div>
```

Change 7 — Ferry Routes list in footer (replace all 7 links with 1):
```tsx
// old
          {/* Ferry Routes */}
          <div>
            <h3 className="font-semibold text-white mb-4">Ferry Routes</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/route/dabhol-dhopave" className="text-gray-400 hover:text-amber-400 transition-colors">Dabhol - Dhopave</Link></li>
              <li><Link href="/route/jaigad-tawsal" className="text-gray-400 hover:text-amber-400 transition-colors">Jaigad - Tawsal</Link></li>
              <li><Link href="/route/dighi-agardande" className="text-gray-400 hover:text-amber-400 transition-colors">Dighi - Agardande</Link></li>
              <li><Link href="/route/veshvi-bagmandale" className="text-gray-400 hover:text-amber-400 transition-colors">Veshvi - Bagmandale</Link></li>
              <li><Link href="/route/vasai-bhayander" className="text-gray-400 hover:text-amber-400 transition-colors">Vasai - Bhayander</Link></li>
              <li><Link href="/route/ambet-mahpral" className="text-gray-400 hover:text-amber-400 transition-colors">Ambet - Mahpral</Link></li>
              <li><Link href="/route/virar-saphale" className="text-gray-400 hover:text-amber-400 transition-colors">Virar - Saphale</Link></li>
            </ul>
          </div>
// new
          {/* Ferry Routes */}
          <div>
            <h3 className="font-semibold text-white mb-4">Ferry Routes</h3>
            <ul className="space-y-2 text-sm">
              <li><Link href="/route/gateway-mandwa" className="text-gray-400 hover:text-amber-400 transition-colors">Gateway of India – Mandwa Jetty</Link></li>
            </ul>
          </div>
```

Change 8 — footer contact email:
```tsx
// old
                <a href="mailto:ssmsdapoli@rediffmail.com" className="text-gray-400 hover:text-amber-400 transition-colors">ssmsdapoli@rediffmail.com</a>
// new
                <a href="mailto:pnpipl11@gmail.com" className="text-gray-400 hover:text-amber-400 transition-colors">pnpipl11@gmail.com</a>
```

Change 9 — footer contact phone:
```tsx
// old
                <a href="tel:+919767248900" className="text-gray-400 hover:text-amber-400 transition-colors">+91 9767248900</a>
// new
                <a href="tel:02222884535" className="text-gray-400 hover:text-amber-400 transition-colors">022-22884535</a>
```

Change 10 — footer address:
```tsx
// old
                <span className="text-gray-400">Dabhol FerryBoat Jetty, Dapoli, Dist. Ratnagiri, Maharashtra - 415712</span>
// new
                <span className="text-gray-400">Apollo Bandar, Colaba, Mumbai MH-400001</span>
```

Change 11 — copyright:
```tsx
// old
            <p>&copy; 2026 Suvarnadurga Shipping &amp; Marine Services. All rights reserved.</p>
// new
            <p>&copy; 2026 PNP Maritime Services Pvt. Ltd. All rights reserved.</p>
```

Change 12 — social link comments:
```tsx
// old
    url: "", // e.g. "https://facebook.com/ssmspl"
// new
    url: "", // e.g. "https://facebook.com/pnpmaritime"
```
```tsx
// old
    url: "", // e.g. "https://instagram.com/ssmspl"
// new
    url: "", // e.g. "https://instagram.com/pnpmaritime"
```
```tsx
// old
    url: "", // e.g. "https://twitter.com/ssmspl"
// new
    url: "", // e.g. "https://twitter.com/pnpmaritime"
```

- [ ] **Step 3: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga\|Dabhol\|Veshvi\|ssmsdapoli\|9767248900\|carferry" \
  frontend/src/components/public/Header.tsx \
  frontend/src/components/public/Footer.tsx
```
Expected: no output

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/public/Header.tsx frontend/src/components/public/Footer.tsx
git commit -m "feat: replace Header and Footer branding with PNP Maritime"
```

---

## Task 6: Frontend Metadata and PWA

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/public/manifest.json`

- [ ] **Step 1: Update layout.tsx metadata**

Change 1:
```tsx
// old
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://carferry.online"
  ),
// new
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_APP_URL || "https://pnp.example.com"
  ),
```

Change 2:
```tsx
// old
  title: "Suvarnadurga Shipping & Marine Services - Ferry Boat Ticketing",
  description:
    "Maharashtra's premier ferry service connecting the Konkan coast since 2003. Book ferry tickets for Dabhol-Dhopave, Jaigad-Tawsal, Dighi-Agardande, and more routes.",
// new
  title: "PNP Maritime Services - Ferry Ticketing | Gateway of India to Mandwa",
  description:
    "Book catamaran ferry tickets from Gateway of India to Mandwa Jetty. AC and Main Deck seating. Includes free bus to Alibag. 7 daily sailings.",
```

Change 3:
```tsx
// old
    title: "SSMSPL Checker",
// new
    title: "PNP Ferry",
```

Change 4 — OpenGraph:
```tsx
// old
    title: "Suvarnadurga Shipping & Marine Services",
    description:
      "Maharashtra's premier ferry service connecting the Konkan coast since 2003.",
// new
    title: "PNP Maritime Services",
    description:
      "Gateway of India to Mandwa Jetty catamaran ferry. Includes free bus to Alibag.",
```

- [ ] **Step 2: Update manifest.json**

Replace the full contents of `frontend/public/manifest.json`:

```json
{
  "name": "PNP Maritime Ferry",
  "short_name": "PNP Ferry",
  "description": "Ferry ticket system for PNP Maritime Services Pvt. Ltd.",
  "start_url": "/dashboard/verify",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#ffffff",
  "theme_color": "#1e3a5f",
  "categories": ["business", "utilities"],
  "icons": [
    {
      "src": "/android-chrome-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/android-chrome-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
```

- [ ] **Step 3: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga\|carferry" frontend/src/app/layout.tsx frontend/public/manifest.json
```
Expected: no output

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/public/manifest.json
git commit -m "feat: update page metadata and PWA manifest for PNP Maritime"
```

---

## Task 7: Frontend Home Page

**Files:**
- Modify: `frontend/src/app/(public)/page.tsx`

- [ ] **Step 1: Replace ROUTES array**

```tsx
// old
const ROUTES = [
  {
    name: "Dabhol – Dhopave",
    slug: "dabhol-dhopave",
    image: "/images/routes/dabhol-dhopave.jpg",
    description:
      "The very first site which was started on 21.10.2003 & constantly working since its first day at all times and in all seasons.",
  },
  {
    name: "Jaigad – Tawsal",
    slug: "jaigad-tawsal",
    image: "/images/routes/jaigad-tawsal.jpg",
    description:
      "This Ferry service was started for the easy & better transportation from Guhagar & Ratnagiri thus making Guhagar tehesil easily accessible.",
  },
  {
    name: "Vasai – Bhayander",
    slug: "vasai-bhayander",
    image: "/images/routes/vasai-bhayander.jpg",
    description:
      "Suvarnadurga Shipping & Marine Ser.Pvt Ltd recently got the opportunity to Serve People in Vasai, Bhayander.This is the SEVENTH route by SSMS",
  },
  {
    name: "Virar – Saphale",
    slug: "virar-saphale",
    image: null,
    description:
      "Suvarnadurga Shipping & Marine Ser.Pvt Ltd proudly introduces its newest milestone, a game changing RORO service between Virar and Saphale (Jalsar).",
  },
  {
    name: "Dighi – Agardande",
    slug: "dighi-agardande",
    image: "/images/routes/dighi-agardande.jpg",
    description:
      "This Ferry service is oriented towards Tourism & Fishing. Many tourists started preferring their weekends at Alibaug & nearby lovely places.",
  },
  {
    name: "Veshvi – Bagmandale",
    slug: "veshvi-bagmandale",
    image: "/images/routes/veshvi-bagmandale.jpg",
    description:
      "This service was started in 2007 & saved lots of time and hassle for transportation from Raigad to Ratnagiri.",
  },
  {
    name: "Ambet – Mahpral",
    slug: "ambet-mahpral",
    image: "/images/routes/ambet-mahpral.jpg",
    description:
      "Ambet \u2013 Mahpral Ferry not only saves Fuel but also saves Time & money as it gives you a Shorter path to travel TOTALLY FREE !!",
    status: "closed" as const,
  },
];
// new
const ROUTES = [
  {
    name: "Gateway of India – Mandwa Jetty",
    slug: "gateway-mandwa",
    image: null,
    description:
      "The fastest sea route from Mumbai to Alibag. A ~45-minute AC catamaran ride from Gateway of India to Mandwa Jetty, followed by a free connecting bus to Alibag ST Stand.",
  },
];
```

- [ ] **Step 2: Replace SERVICES array**

```tsx
// old
const SERVICES = [
  {
    title: "Enjoy Our Cruise Service",
    subtitle: "Give it a Go !",
    image: "/images/backgrounds/cruise-services.jpg",
    description:
      "Now a days tourism had flourished well in \u2018Konkan Region\u2019. Tourist are always seeking for something new and exciting. Keeping in view this need, we have started CRUISE service like Goa- cruise at various seasons.",
    extra:
      "A programme of about an hour, consists various entertaining programs and cultural activities like Kokani Cultural Events, Goan Fusion, DJ night, Deck Dance for couples, Special games for kids, various Game Shows along with fresh Kokani delicious food on cruise.\nBeing a seasonal service, arrangements are made only during some months & advance booking is necessary for hassle free experience.",
  },
  {
    title: "Exclusive Inland Service",
    image: "/images/backgrounds/inland-services.jpg",
    description:
      "This is a special transportation service for various Materials & Machines at desirable locations.",
  },
  {
    title: "Easy Transportation",
    image: "/images/backgrounds/inland-services.jpg",
    description:
      "As there are many ports in Kokan region, transportation of various products from one location to another through sea has become a necessity. Ferry-Service comes to help for transporting heavy machines like cranes, fork lanes (JCB), boaring machines, large tankers or any other heavy material which is tedious to transport by road.",
    extra:
      "As this is a special service, charges depend upon weight, distance, waiting time, fuel & labour etc.\nThis service is started for the economic transportation of heavy materials conveniently through water with proper safety.",
  },
];
// new
const SERVICES = [
  {
    title: "Charter & Tourist Trips",
    subtitle: "Private Sailings Available",
    image: "/images/backgrounds/cruise-services.jpg",
    description:
      "PNP Maritime offers private catamaran charters for corporate events, family outings, and special occasions. Enjoy the scenic Mumbai harbour aboard our AC catamarans.",
    extra:
      "Advance booking required. Contact our Gateway of India office at 022-22884535 for charter enquiries and pricing. [CONFIRM WITH CLIENT]",
  },
  {
    title: "Port Operations",
    image: "/images/backgrounds/inland-services.jpg",
    description:
      "PNP also operates a multipurpose port at Dharamtar, Raigad, handling cargo including coal, steel coils, and cement with an annual throughput capacity of ~4 Mtpa. [CONFIRM WITH CLIENT]",
  },
];
```

- [ ] **Step 3: Update hero text**

Change 1:
```tsx
// old
              Maharashtra&apos;s Premier Ferry Service
// new
              Mumbai&apos;s Premier Catamaran Service
```

Change 2:
```tsx
// old
            Experience seamless ferry travel across Maharashtra&apos;s beautiful
            Konkan coast. Safe, reliable, and scenic journeys since 2003.
// new
            Experience fast catamaran travel from Gateway of India to Mandwa Jetty.
            AC and non-AC seating available. Includes free bus to Alibag.
```

- [ ] **Step 4: Update Routes section headings**

Change 1:
```tsx
// old
              Ferry Services Across Konkan
// new
              Ferry Services
```

Change 2:
```tsx
// old
              Connecting Maharashtra&apos;s beautiful coastal communities with
              reliable ferry services since 2003.
// new
              Connecting Mumbai to Alibag with fast, comfortable catamaran service since 1999.
```

- [ ] **Step 5: Update "Why Choose Us" bullets and stats**

Change 1 — bullets array:
```tsx
// old
                {[
                  {
                    title: "Safe & Reliable",
                    text: "All ferries meet strict safety standards with trained crew",
                  },
                  {
                    title: "On-Time Service",
                    text: "Running 7 days a week with reliable schedules",
                  },
                  {
                    title: "Vehicle Transport",
                    text: "RORO ferries for cars, bikes, and commercial vehicles",
                  },
                  {
                    title: "Since 2003",
                    text: "Over 20 years serving coastal communities",
                  },
                ].map((item) => (
// new
                {[
                  {
                    title: "Safe & Reliable",
                    text: "All catamarans meet Maharashtra Maritime Board safety standards",
                  },
                  {
                    title: "On-Time Service",
                    text: "7 daily sailings each direction, 365 days a year",
                  },
                  {
                    title: "AC Catamaran",
                    text: "The only AC catamaran service on the Gateway–Mandwa route",
                  },
                  {
                    title: "Since 1999",
                    text: "Over 25 years serving Mumbai–Alibag travellers",
                  },
                ].map((item) => (
```

Change 2 — stats grid:
```tsx
// old
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">20+</div>
                <div className="text-gray-300 text-sm">Years of Service</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">7</div>
                <div className="text-gray-300 text-sm">Active Routes</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">65+</div>
                <div className="text-gray-300 text-sm">Employees</div>
              </div>
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">1M+</div>
                <div className="text-gray-300 text-sm">Passengers Served</div>
              </div>
// new
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">25+</div>
                <div className="text-gray-300 text-sm">Years of Service</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">1</div>
                <div className="text-gray-300 text-sm">Active Route</div>
              </div>
              <div className="bg-gradient-to-br from-[#0f3a50] to-[#1a5c7a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">350+</div>
                <div className="text-gray-300 text-sm">Passengers Per Sailing</div>
              </div>
              <div className="bg-gradient-to-br from-[#0c3547] to-[#1a6b8a] rounded-2xl p-6 md:p-8 text-center">
                <div className="text-3xl md:text-4xl font-bold text-amber-400 mb-1">1M+</div>
                <div className="text-gray-300 text-sm">Passengers Served</div>
              </div>
```

- [ ] **Step 6: Update About section**

Change 1 — heading:
```tsx
// old
              About Suvarnadurga Shipping
// new
              About PNP Maritime
```

Change 2 — about section body content:
```tsx
// old
              <p className="text-gray-300 leading-relaxed mb-3">
                Suvarnadurga Shipping &amp; Marine Services Pvt. Ltd. is a Company which is started by Dr. Mokal C.J. (Ex. MLA, Dapoli &ndash; Mandangad) with Dr. Mokal Y.C. as a Managing Director, in October 2003. We have skilled Staff of about 65 at different sites.
              </p>
              <p className="text-gray-300 leading-relaxed mb-3">
                We have approved Ticket Rates &amp; all necessary permits by Maharashtra Maritime board with Annual Inspections for requirements on Ferry Boat. Company is very particular about all life guarding apparatus on Ferry boat, for the safety of tourists &amp; public.
              </p>
              <p className="text-gray-300 leading-relaxed mb-3">
                We began by starting a Ferry-Boat Service at Dabhol-Dhopave, which was a first Ferry Boat Service in Maharashtra. After Successful Service in Dabhol; we started another service in Veshvi &ndash; Bagmandle, then Tawsal &ndash; Jaigad, and Rohini &ndash; Agardande.
              </p>
              <p className="text-gray-300 leading-relaxed mb-5">
                Suvarnadurga Shipping and Marine Services is the transportation company that serves the Nation &amp; saves most valuable fuel. We hope, you will enjoy our Safe, Quick and Refreshing Ferry Services all the time.
              </p>
// new
              <p className="text-gray-300 leading-relaxed mb-3">
                PNP Maritime Services Pvt. Ltd. has been connecting Mumbai to the Konkan coast since 1999. We operate the only air-conditioned catamaran service on the Gateway of India to Mandwa Jetty route.
              </p>
              <p className="text-gray-300 leading-relaxed mb-3">
                Our catamarans accommodate over 350 passengers per sailing across two seating options — Main Deck and AC Deck. All vessels are approved by the Maharashtra Maritime Board and undergo annual safety inspections.
              </p>
              <p className="text-gray-300 leading-relaxed mb-5">
                Every sailing includes a complimentary connecting bus from Mandwa Jetty to Alibag ST Stand, making the complete Mumbai–Alibag journey seamlessly connected in under 2 hours.
              </p>
```

Change 3 — badges:
```tsx
// old
                  <span className="text-sm font-medium text-white">65+ Employees</span>
// new
                  <span className="text-sm font-medium text-white">350+ Capacity</span>
```

```tsx
// old
                  <span className="text-sm font-medium text-white">7 Active Routes</span>
// new
                  <span className="text-sm font-medium text-white">1 Active Route</span>
```

```tsx
// old
                  <span className="text-sm font-medium text-white">1000s of Daily Passengers</span>
// new
                  <span className="text-sm font-medium text-white">Daily Service</span>
```

- [ ] **Step 7: Fix routes grid layout** — Since we now have 1 route instead of 7, the 3+4 grid split no longer makes sense. Replace the two-row grid with a single centered card:

```tsx
// old
          {/* First row: 3 cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            {ROUTES.slice(0, 3).map((route) => (
              <div
// new
          <div className="grid grid-cols-1 gap-6 mb-6 max-w-lg mx-auto">
            {ROUTES.slice(0, 3).map((route) => (
              <div
```

Also remove the second row grid entirely:
```tsx
// old
          {/* Second row: 4 cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {ROUTES.slice(3).map((route) => (
              <div
                key={route.name}
                className="group bg-white rounded-xl shadow-md hover:shadow-xl transition-all duration-300 overflow-hidden border border-gray-100"
              >
                <div className="relative h-40 overflow-hidden bg-gradient-to-br from-[#0c3547] to-[#1a6b8a]">
                  {route.image ? (
                    <Image
                      src={route.image}
                      alt={route.name}
                      fill
                      sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"
                      className="object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <svg className="w-12 h-12 text-white/20" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20 21c-1.39 0-2.78-.47-4-1.32-2.44 1.71-5.56 1.71-8 0C6.78 20.53 5.39 21 4 21H2v-2h2c1.38 0 2.74-.35 4-.99 2.52 1.29 5.48 1.29 8 0 1.26.65 2.62.99 4 .99h2v2h-2zM3.95 19H4c1.6 0 3.02-.88 4-2 .98 1.12 2.4 2 4 2s3.02-.88 4-2c.98 1.12 2.4 2 4 2h.05l1.89-6.68c.08-.26.06-.54-.06-.78s-.34-.42-.6-.5L20 10.62V6c0-1.1-.9-2-2-2h-3V1H9v3H6c-1.1 0-2 .9-2 2v4.62l-1.29.42a1.007 1.007 0 00-.66 1.28L3.95 19zM6 6h12v3.97L12 8 6 9.97V6z" />
                      </svg>
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                  {"status" in route && route.status === "closed" && (
                    <span className="absolute top-3 right-3 bg-red-500 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full">
                      Closed
                    </span>
                  )}
                  <div className="absolute bottom-3 left-3">
                    <span className="bg-gradient-to-r from-amber-500 to-orange-500 text-white text-[10px] font-bold px-2.5 py-1 rounded-full">
                      {route.name}
                    </span>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="text-base font-bold text-slate-900 mb-1.5">
                    {route.name}
                  </h3>
                  <p className="text-gray-500 text-xs leading-relaxed mb-2 line-clamp-3">
                    {route.description}
                  </p>
                  <Link
                    href={`/route/${route.slug}`}
                    className="text-sky-600 text-xs font-semibold hover:text-sky-800 transition-colors"
                  >
                    Know More &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
// new (delete this entire block — no second row needed with 1 route)
```

- [ ] **Step 8: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga\|Dabhol\|Dhopave\|Jaigad\|Veshvi\|Vasai\|Ambet\|Virar\|2003\|carferry" \
  "frontend/src/app/(public)/page.tsx"
```
Expected: no output

- [ ] **Step 9: Commit**

```bash
git add "frontend/src/app/(public)/page.tsx"
git commit -m "feat: rewrite home page content for PNP Maritime"
```

---

## Task 8: Frontend About Page

**Files:**
- Modify: `frontend/src/app/(public)/about/page.tsx`

- [ ] **Step 1: Replace ferryRoutes array**

```tsx
// old
const ferryRoutes = [
  "Dabhol \u2013 Dhopave",
  "Jaigad \u2013 Tawsal",
  "Dighi \u2013 Agardande",
  "Veshvi \u2013 Bagmandale",
  "Vasai \u2013 Bhayander",
  "Virar \u2013 Saphale (Jalsar)",
  "Ambet \u2013 Mahpral",
];
// new
const ferryRoutes = [
  "Gateway of India \u2013 Mandwa Jetty (incl. free bus to Alibag)",
];
```

- [ ] **Step 2: Replace stats array**

```tsx
// old
const stats = [
  { value: "20+", label: "YEARS OF SERVICE" },
  { value: "7", label: "FERRY ROUTES" },
  { value: "65+", label: "EMPLOYEES" },
  { value: "1M+", label: "PASSENGERS SERVED" },
];
// new
const stats = [
  { value: "25+", label: "YEARS OF SERVICE" },
  { value: "1", label: "FERRY ROUTE" },
  { value: "350+", label: "CAPACITY PER SAILING" },
  { value: "1M+", label: "PASSENGERS SERVED" },
];
```

- [ ] **Step 3: Update banner subtitle**

```tsx
// old
            Maharashtra&apos;s First Ferry Boat Service Since 2003
// new
            Gateway to Alibag &mdash; Catamaran Ferry Since 1999
```

- [ ] **Step 4: Update "Who We Are" heading and description**

```tsx
// old
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-6">
            Suvarnadurga Shipping &amp; Marine Services Pvt. Ltd.
          </h2>
          <p className="text-gray-600 leading-relaxed text-base md:text-lg">
            Suvarnadurga Shipping and Marine Services is the transportation company that serves the Nation &amp; saves most valuable fuel.
          </p>
// new
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-6">
            PNP Maritime Services Pvt. Ltd.
          </h2>
          <p className="text-gray-600 leading-relaxed text-base md:text-lg">
            PNP Maritime Services is a government-approved catamaran ferry operator providing fast, comfortable sea travel between Gateway of India (Mumbai) and Mandwa Jetty, with a free connecting bus to Alibag.
          </p>
```

- [ ] **Step 5: Replace "Our Story" content**

```tsx
// old
              <div className="space-y-4 text-gray-600 leading-relaxed">
                <p>
                  Suvarnadurga Shipping &amp; Marine Services Pvt. Ltd. is a Company which is started by Dr. Mokal C.J. (Ex. MLA, Dapoli &ndash; Mandangad) with Dr. Mokal Y.C. as a Managing Director, in October 2003. We have skilled Staff of about 65 at different sites. We have approved Ticket Rates &amp; all necessary permits by Maharashtra Maritime board with Annual Inspections for requirements on Ferry Boat. Company is very particular about all life guarding apparatus on Ferry boat, for the safety of tourists &amp; public. Company Pay the Tax in the form of leavy by each ferry boat to the Government of about- four lakhs per year.
                </p>
                <p>
                  We began by starting a Ferry-Boat Service at Dabhol-Dhopave, which was a first Ferry Boat Service in Maharashtra. Before this ferry boat service there was no substitute for Dapoli to Guhagar journey, except Straight Highway (NH. 17) &amp; that was too expensive in the form of money &amp; time. Using ferry boat, you save a road journey by about 3 hrs. &amp; fuel as well. Its also a relief from cumbersome Road Traffic &amp; mishaps on the highway.
                </p>
                <p>
                  After Successful Service in Dabhol; we started another service in Veshvi &ndash; Bagmandle. This time we made a shortcut for traveling from Veshvi (Ratnagiri) to Bagmandle (Raigad). By the time, we had great confidence in our services, and we started a new ferry at Tawsal (Guhagar) to Jaigad (Ratnagiri). After this huge success we took an advantage to start ferry services At Rohini &ndash; Agardande.
                </p>
                <p>
                  Suvarnadurga Shipping and Marine Services is the transportation company that serves the Nation &amp; saves most valuable fuel. We hope, you will enjoy our Safe, Quick and Refreshing Ferry Services all the time.
                </p>
              </div>
// new
              <div className="space-y-4 text-gray-600 leading-relaxed">
                <p>
                  PNP Maritime Services Pvt. Ltd. (CIN: U63090MH1999PTC121461) was incorporated on 25th August 1999 with a vision to provide comfortable, reliable sea travel between Mumbai and the Konkan coast.
                </p>
                <p>
                  PNP operates the only air-conditioned catamaran service on the Gateway of India to Mandwa Jetty route. Our catamarans accommodate over 350 passengers per sailing, offering two seating classes &mdash; Main Deck and AC Deck. All vessels are approved by the Maharashtra Maritime Board and undergo annual safety inspections. {/* [CONFIRM WITH CLIENT: additional history, founding story] */}
                </p>
                <p>
                  To make the full Mumbai&ndash;Alibag journey seamless, every sailing includes a complimentary connecting bus service from Mandwa Jetty to Alibag ST Stand. Passengers reach Alibag from Gateway of India in under 2 hours, avoiding the long road route entirely.
                </p>
                <p>
                  With 7 daily sailings in each direction, 365 days a year, PNP Maritime remains the preferred choice for thousands of passengers travelling between Mumbai and Alibag. {/* [CONFIRM WITH CLIENT: passenger volume, fleet size] */}
                </p>
              </div>
```

- [ ] **Step 6: Update contact bar (section 7 of about page)**

Change 1 — Head Office block:
```tsx
// old
            <p className="text-white/90 text-sm">
              Dabhol FerryBoat Jetty, Dapoli
            </p>
            <p className="text-white/90 text-sm">
              Dist. Ratnagiri, Maharashtra - 415712
            </p>
// new
            <p className="text-white/90 text-sm">
              Apollo Bandar, Colaba
            </p>
            <p className="text-white/90 text-sm">
              Mumbai MH-400001
            </p>
```

Change 2 — Contact Numbers block:
```tsx
// old
              <a
                href="tel:02348248900"
                className="hover:text-white transition-colors"
              >
                02348-248900
              </a>
// new
              <a
                href="tel:02222884535"
                className="hover:text-white transition-colors"
              >
                022-22884535
              </a>
```

```tsx
// old
              <a
                href="tel:+919767248900"
                className="hover:text-white transition-colors"
              >
                +91 9767248900
              </a>
// new
              <a
                href="tel:+918591254683"
                className="hover:text-white transition-colors"
              >
                +91 8591254683
              </a>
```

Change 3 — Email Us block (remove second email y.mokal@rediffmail.com):
```tsx
// old
            <p className="text-white/90 text-sm">
              <a
                href="mailto:ssmsdapoli@rediffmail.com"
                className="hover:text-white transition-colors"
              >
                ssmsdapoli@rediffmail.com
              </a>
            </p>
            <p className="text-white/90 text-sm">
              <a
                href="mailto:y.mokal@rediffmail.com"
                className="hover:text-white transition-colors"
              >
                y.mokal@rediffmail.com
              </a>
            </p>
// new
            <p className="text-white/90 text-sm">
              <a
                href="mailto:pnpipl11@gmail.com"
                className="hover:text-white transition-colors"
              >
                pnpipl11@gmail.com
              </a>
            </p>
```

Change 4 — "Reliable Service" commitment description (2003 reference):
```tsx
// old
      "Operating 7 days a week, in all seasons. Our ferries have been running continuously since 2003 with minimal disruptions.",
// new
      "Operating 7 days a week with 7 daily sailings each direction. Continuous service since 1999 with minimal disruptions.",
```

- [ ] **Step 7: Verify**

```bash
grep -n "SSMSPL\|Suvarnadurga\|Dabhol\|Veshvi\|Jaigad\|ssmsdapoli\|y\.mokal\|9767248900\|2003" \
  "frontend/src/app/(public)/about/page.tsx"
```
Expected: no output

- [ ] **Step 8: Commit**

```bash
git add "frontend/src/app/(public)/about/page.tsx"
git commit -m "feat: rewrite About page for PNP Maritime"
```

---

## Task 9: Frontend Route Page

**Files:**
- Modify: `frontend/src/app/(public)/route/[slug]/page.tsx`

- [ ] **Step 1: Replace the entire ROUTE_DATA object**

The ROUTE_DATA object in this file contains all 7 SSMSPL route entries. Replace the entire object (from `const ROUTE_DATA: Record<string, RouteInfo> = {` through its closing `};`) with:

```tsx
const ROUTE_DATA: Record<string, RouteInfo> = {
  "gateway-mandwa": {
    name: "Gateway of India \u2013 Mandwa Jetty",
    subtitle: "The fastest sea route from Mumbai to Alibag. ~45 min catamaran + free connecting bus.",
    image: null,
    about: [
      "PNP Maritime Services operates the only air-conditioned catamaran service from Gateway of India, Apollo Bandar, Mumbai, to Mandwa Jetty, Alibaug. The crossing takes approximately 45\u201355 minutes, offering passengers spectacular views of the Mumbai harbour and the open sea.",
      "Gateway of India is one of Mumbai\u2019s most iconic landmarks, located at Apollo Bandar, Colaba. Ferries depart from the jetty adjacent to the monument, making it easily accessible from South Mumbai by bus, taxi, or local train to Churchgate.",
      "Upon arrival at Mandwa Jetty, passengers board a complimentary PNP bus that connects directly to Alibag ST Stand. The bus journey takes approximately 40\u201345 minutes, completing the full Mumbai\u2013Alibag journey in under 2 hours \u2014 far faster and more scenic than the road route.",
      "Alibag is a popular weekend destination from Mumbai, known for its beaches, forts, and seafood. The Kolaba Fort (accessible by foot at low tide), Alibag beach, and Varsoli beach are among the top attractions. Murud-Janjira Fort, Kashid Beach, and Revdanda are also accessible from Alibag.",
    ],
    tourist:
      "Popular destinations near Alibag: Kolaba Fort, Alibag Beach, Varsoli Beach, Kashid Beach (45 km), Murud-Janjira Fort (55 km), Revdanda Fort, and Harihareshwar. Alibag is also known for fresh seafood and Konkani cuisine.",
    contacts: [
      { label: "Gateway of India Office", phones: ["022-22884535", "022-22885220", "+91 8591254683"] },
      { label: "Mandwa Jetty Office", phones: ["02141-237087", "02141-237464"] },
      { label: "Alibag Office", phones: ["02141-225403", "+91 8805401558"] },
    ],
    timetableImage: null,
    ratecardImage: null,
  },
};
```

- [ ] **Step 2: Verify**

```bash
grep -n "Suvarnadurga\|SSMSPL\|dabhol\|dhopave\|jaigad\|veshvi\|vasai\|ambet\|virar" \
  "frontend/src/app/(public)/route/[slug]/page.tsx"
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/app/(public)/route/[slug]/page.tsx"
git commit -m "feat: replace route page data with PNP Gateway-Mandwa route"
```

---

## Task 10: Frontend Contact Page

**Files:**
- Modify: `frontend/src/app/(public)/contact/page.tsx`

- [ ] **Step 1: Replace ROUTES array**

```tsx
// old
const ROUTES = [
  {
    name: "Dabhol \u2013 Dhopave",
    phones: ["02348-248900", "9767248900", "7709250800"],
  },
  {
    name: "Jaigad \u2013 Tawsal",
    phones: ["02354-242500", "8550999884", "8550999880"],
  },
  {
    name: "Dighi \u2013 Agardande",
    phones: ["9156546700", "8550999887"],
  },
  {
    name: "Veshvi \u2013 Bagmandale",
    phones: ["02350-223300", "8767980300", "9322819161"],
  },
  {
    name: "Vasai \u2013 Bhayander",
    phones: ["8624063900", "8600314710"],
  },
  {
    name: "Ambet \u2013 Mahpral",
    phones: ["8624063900", "7709250800"],
  },
  {
    name: "Virar \u2013 Saphale",
    phones: ["9371002900", "8459803521"],
  },
];
// new
const ROUTES = [
  {
    name: "Gateway of India Office",
    phones: ["022-22884535", "022-22885220", "+91 8591254683"],
  },
  {
    name: "Mandwa Jetty Office",
    phones: ["02141-237087", "02141-237464"],
  },
  {
    name: "Alibag Office",
    phones: ["02141-225403", "+91 8805401558"],
  },
];
```

- [ ] **Step 2: Verify**

```bash
grep -n "Dabhol\|Dhopave\|Jaigad\|Veshvi\|Vasai\|Ambet\|Virar\|9767248900\|ssmsdapoli" \
  "frontend/src/app/(public)/contact/page.tsx"
```
Expected: no output

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/app/(public)/contact/page.tsx"
git commit -m "feat: replace contact page phone numbers and offices with PNP Maritime contacts"
```

---

## Task 11: Frontend Customer Portal Pages

**Files:**
- Modify: `frontend/src/app/customer/login/page.tsx`
- Modify: `frontend/src/app/customer/register/page.tsx`
- Modify: `frontend/src/app/customer/forgot-password/page.tsx`
- Modify: `frontend/src/app/customer/reset-password/page.tsx`
- Modify: `frontend/src/app/customer/verify-email/page.tsx`

Each of these files has the same 3 patterns to replace. Apply to all 5 files:

- [ ] **Step 1: Apply changes to login/page.tsx**

Change 1 — logo alt (line 127):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name in heading (line 133):
```tsx
// old
                SSMSPL
// new
                PNP Maritime
```

Change 3 — "New to SSMSPL?" text (line 258):
```tsx
// old
                <span className="px-4 text-white/40">New to SSMSPL?</span>
// new
                <span className="px-4 text-white/40">New to PNP Maritime?</span>
```

Change 4 — copyright (line 285):
```tsx
// old
            &copy; {new Date().getFullYear()} SSMSPL. All rights reserved.
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights reserved.
```

- [ ] **Step 2: Apply changes to register/page.tsx**

Change 1 — logo alt (line 181):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name (line 187):
```tsx
// old
                SSMSPL
// new
                PNP Maritime
```

Change 3 — copyright (line 405):
```tsx
// old
            &copy; {new Date().getFullYear()} SSMSPL. All rights reserved.
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights reserved.
```

- [ ] **Step 3: Apply changes to forgot-password/page.tsx**

Change 1 — logo alt (line 168):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name (line 173):
```tsx
// old
              <span className="text-3xl font-bold text-white tracking-tight">SSMSPL</span>
// new
              <span className="text-3xl font-bold text-white tracking-tight">PNP Maritime</span>
```

Change 3 — copyright (line 390):
```tsx
// old
            &copy; {new Date().getFullYear()} SSMSPL. All rights reserved.
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights reserved.
```

- [ ] **Step 4: Apply changes to reset-password/page.tsx**

Change 1 — logo alt (line 43):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name (line 48):
```tsx
// old
              <span className="text-3xl font-bold text-white tracking-tight">SSMSPL</span>
// new
              <span className="text-3xl font-bold text-white tracking-tight">PNP Maritime</span>
```

Change 3 — copyright (line 72):
```tsx
// old
            &copy; {new Date().getFullYear()} SSMSPL. All rights reserved.
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights reserved.
```

- [ ] **Step 5: Apply changes to verify-email/page.tsx**

Change 1 — logo alt (line 258):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name (line 263):
```tsx
// old
              <span className="text-3xl font-bold text-white tracking-tight">SSMSPL</span>
// new
              <span className="text-3xl font-bold text-white tracking-tight">PNP Maritime</span>
```

Change 3 — copyright (line 278):
```tsx
// old
            &copy; {new Date().getFullYear()} SSMSPL. All rights reserved.
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights reserved.
```

- [ ] **Step 6: Verify all 5 files**

```bash
grep -rn "SSMSPL\|Suvarnadurga" \
  frontend/src/app/customer/login/page.tsx \
  frontend/src/app/customer/register/page.tsx \
  frontend/src/app/customer/forgot-password/page.tsx \
  frontend/src/app/customer/reset-password/page.tsx \
  frontend/src/app/customer/verify-email/page.tsx
```
Expected: no output

- [ ] **Step 7: Commit**

```bash
git add \
  frontend/src/app/customer/login/page.tsx \
  frontend/src/app/customer/register/page.tsx \
  frontend/src/app/customer/forgot-password/page.tsx \
  frontend/src/app/customer/reset-password/page.tsx \
  frontend/src/app/customer/verify-email/page.tsx
git commit -m "feat: replace SSMSPL branding in customer portal auth pages with PNP Maritime"
```

---

## Task 12: Frontend Dashboard Components

**Files:**
- Modify: `frontend/src/components/customer/CustomerLayout.tsx`
- Modify: `frontend/src/components/dashboard/AppSidebar.tsx`
- Modify: `frontend/src/components/Navbar.tsx`

- [ ] **Step 1: Update CustomerLayout.tsx**

Change 1 — logo alt (line 118):
```tsx
// old
                alt="Suvarnadurga Shipping"
// new
                alt="PNP Maritime Services"
```

Change 2 — brand name (line 124):
```tsx
// old
                SSMSPL
// new
                PNP Maritime
```

Change 3 — copyright (line 331):
```tsx
// old
            &copy; {new Date().getFullYear()} Suvarnadurga Shipping. All rights
// new
            &copy; {new Date().getFullYear()} PNP Maritime Services Pvt. Ltd. All rights
```

- [ ] **Step 2: Update AppSidebar.tsx**

There are 2 occurrences of the logo block in AppSidebar (expanded and collapsed states). For each:

Change 1 — first alt (line 245):
```tsx
// old (first occurrence)
                alt="SSMSPL"
              />
              </div>
            <div className="overflow-hidden transition-all">
              <span
                className="font-bold text-foreground whitespace-nowrap"
              >
                SSMSPL
// new
                alt="PNP Maritime"
              />
              </div>
            <div className="overflow-hidden transition-all">
              <span
                className="font-bold text-foreground whitespace-nowrap"
              >
                PNP Maritime
```

Change 2 — second alt (line 279):
```tsx
// old (second occurrence)
                  alt="SSMSPL"
                />
              </div>
              <div className="overflow-hidden transition-all duration-200">
                <span className="font-semibold text-foreground text-sm whitespace-nowrap">
                  SSMSPL
// new
                  alt="PNP Maritime"
                />
              </div>
              <div className="overflow-hidden transition-all duration-200">
                <span className="font-semibold text-foreground text-sm whitespace-nowrap">
                  PNP Maritime
```

- [ ] **Step 3: Update Navbar.tsx**

Change 1 — logo alt (line 33):
```tsx
// old
          alt="Suvarnadurga Shipping"
// new
          alt="PNP Maritime Services"
```

Change 2 — brand text (line 39):
```tsx
// old
          <span className="text-xl font-bold tracking-wide">SSMSPL</span>
// new
          <span className="text-xl font-bold tracking-wide">PNP Maritime</span>
```

- [ ] **Step 4: Verify**

```bash
grep -rn "SSMSPL\|Suvarnadurga" \
  frontend/src/components/customer/CustomerLayout.tsx \
  frontend/src/components/dashboard/AppSidebar.tsx \
  frontend/src/components/Navbar.tsx
```
Expected: no output

- [ ] **Step 5: Commit**

```bash
git add \
  frontend/src/components/customer/CustomerLayout.tsx \
  frontend/src/components/dashboard/AppSidebar.tsx \
  frontend/src/components/Navbar.tsx
git commit -m "feat: replace SSMSPL branding in CustomerLayout, AppSidebar, and Navbar"
```

---

## Task 13: Frontend Dashboard Pages

**Files:**
- Modify: `frontend/src/app/dashboard/branches/page.tsx`
- Modify: `frontend/src/app/dashboard/ticketing/page.tsx`
- Modify: `frontend/src/app/dashboard/settings/components/backups-tab.tsx`
- Modify: `frontend/src/app/dashboard/settings/components/notifications-tab.tsx`
- Modify: `frontend/src/app/dashboard/users/page.tsx`

- [ ] **Step 1: Update branches/page.tsx — PDF and HTML exports**

Change 1 (line 238):
```tsx
// old
<html><head><title>SSMSPL - Branch List</title>
// new
<html><head><title>PNP - Branch List</title>
```

Change 2 (line 249):
```tsx
// old
<h1>SSMSPL - Branch List</h1>
// new
<h1>PNP - Branch List</h1>
```

Change 3 (line 267):
```tsx
// old
      doc.text("SSMSPL - Branch List", 14, 15);
// new
      doc.text("PNP - Branch List", 14, 15);
```

- [ ] **Step 2: Update ticketing/page.tsx — QZ certificate link text**

Change 1 (line 2516 — link text only, NOT the href):
```tsx
// old
                    <li>Download the <a href="/ssmspl-qz.crt" download className="text-blue-600 underline">SSMSPL certificate</a> below</li>
// new
                    <li>Download the <a href="/ssmspl-qz.crt" download className="text-blue-600 underline">PNP certificate</a> below</li>
```

Change 2 (line 2543 — download link text):
```tsx
// old
              <a href="/ssmspl-qz.crt" download>
// new (no change to href — keep ssmspl-qz.crt as the actual server file)
              <a href="/ssmspl-qz.crt" download>
```
(No change needed here — the file path is internal.)

- [ ] **Step 3: Update settings placeholder emails**

In `backups-tab.tsx` (line 453):
```tsx
// old
                placeholder="e.g. admin@ssmspl.com"
// new
                placeholder="e.g. admin@pnp.example.com"
```

In `notifications-tab.tsx` (line 151):
```tsx
// old
              placeholder="e.g. admin@ssmspl.com"
// new
              placeholder="e.g. admin@pnp.example.com"
```

In `users/page.tsx` (line 578):
```tsx
// old
                placeholder="e.g. john@ssmspl.com (optional)"
// new
                placeholder="e.g. john@pnp.example.com (optional)"
```

- [ ] **Step 4: Verify**

```bash
grep -rn "SSMSPL\|Suvarnadurga" \
  frontend/src/app/dashboard/branches/page.tsx \
  frontend/src/app/dashboard/ticketing/page.tsx \
  frontend/src/app/dashboard/settings/components/backups-tab.tsx \
  frontend/src/app/dashboard/settings/components/notifications-tab.tsx \
  frontend/src/app/dashboard/users/page.tsx
```
Expected: only `/ssmspl-qz.crt` href references (intentionally kept) — no visible text references.

- [ ] **Step 5: Commit**

```bash
git add \
  frontend/src/app/dashboard/branches/page.tsx \
  frontend/src/app/dashboard/ticketing/page.tsx \
  frontend/src/app/dashboard/settings/components/backups-tab.tsx \
  frontend/src/app/dashboard/settings/components/notifications-tab.tsx \
  frontend/src/app/dashboard/users/page.tsx
git commit -m "feat: replace SSMSPL references in dashboard pages and settings"
```

---

## Task 14: Frontend Print Receipt

**Files:**
- Modify: `frontend/src/lib/print-receipt.ts`

- [ ] **Step 1: Update website URL in receipt footer (line 288)**

```ts
// old
<div class="center note">HAPPY JOURNEY - www.carferry.online</div>
// new
<div class="center note">HAPPY JOURNEY - www.pnp.example.com</div>
```

Note: The Marathi disclaimer text ("Tantrik Durustimule...") and `data-ssmspl-receipt` CSS attributes are kept unchanged — these are internal identifiers and the Marathi text is an operational notice.

- [ ] **Step 2: Verify**

```bash
grep -n "carferry\.online\|SSMSPL\|Suvarnadurga" frontend/src/lib/print-receipt.ts
```
Expected: no output (internal `data-ssmspl-receipt` CSS selectors are exempt as they are not user-visible text)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/print-receipt.ts
git commit -m "feat: update receipt footer URL from carferry.online to pnp.example.com"
```

---

## Task 15: Final Verification Sweep

- [ ] **Step 1: Run comprehensive grep across all user-visible files**

```bash
grep -rn "SSMSPL\|Suvarnadurga\|suvarnadurga\|carferry\.online\|ssmsdapoli\|9767248900\|y\.mokal\|Dabhol\|Dhopave\|Jaigad\|Tawsal\|Veshvi\|Bagmandale\|Vasai\|Bhayander\|Ambet\|Mhapral\|Virar\|Safale" \
  frontend/src/app/ \
  frontend/src/components/ \
  frontend/public/manifest.json \
  frontend/src/lib/print-receipt.ts \
  backend/app/config.py \
  backend/app/main.py \
  backend/app/services/email_service.py \
  backend/app/services/daily_report_service.py \
  backend/app/services/ccavenue_service.py \
  backend/scripts/seed_data.sql \
  2>/dev/null | grep -v "node_modules" | grep -v ".next"
```

Expected: **zero matches** (or only `/ssmspl-qz.crt` href and internal `data-ssmspl-receipt`/`ssmspl_` localStorage key references which are intentionally kept)

- [ ] **Step 2: If any matches found** — fix them before proceeding

- [ ] **Step 3: Update CLAUDE.md to reflect the PNP project**

The existing CLAUDE.md still describes this as "SSMSPL". Update the Project Overview section to reflect PNP Maritime:

```markdown
# old
## Project Overview

SSMSPL (Suvarnadurga Shipping & Marine Services Pvt. Ltd.) — Ferry Boat Ticketing System. Full-stack monorepo with a FastAPI async backend and Next.js frontend communicating via REST API.

# new
## Project Overview

PNP Maritime Services Pvt. Ltd. — Ferry Boat Ticketing System. White-labeled from SSMSPL platform. Full-stack monorepo with a FastAPI async backend and Next.js frontend communicating via REST API. Internal naming (DB, cookies, bundle IDs) retains `ssmspl_` prefix by design.
```

- [ ] **Step 4: Final commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md project overview for PNP Maritime white-label"
```

---

## Post-Implementation Checklist (Manual Steps)

These cannot be automated and must be done manually:

- [ ] **Logo files** — Obtain PNP logo from client and overwrite:
  - `frontend/public/images/logos/logo.png`
  - `frontend/public/images/logos/logo-white.png`
  - `frontend/public/favicon-16x16.png`, `favicon-32x32.png`
  - `frontend/public/apple-touch-icon.png`
  - `frontend/public/android-chrome-192x192.png`, `android-chrome-512x512.png`
  - `frontend/public/og-image.png`
  - `backend/logo.png`
  - `backend/logo_qr_code.png`

- [ ] **Domain** — Replace `pnp.example.com` with actual domain once confirmed
- [ ] **Passenger rates** — Confirm Rs. 285 (Main Deck) and Rs. 325 (AC Deck) with client, update seed_data.sql
- [ ] **Route images / timetable images** — Client to provide; place at `frontend/public/images/routes/` and `frontend/public/images/timetables/`
- [ ] **SMTP credentials** — Configure actual email for password reset and OTP flows
- [ ] **CCAvenue credentials** — Configure for production payments
- [ ] **Bus route** — Confirm with client whether to add Mandwa → Alibag as Route 2
