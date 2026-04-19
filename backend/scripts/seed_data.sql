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
INSERT INTO users (id, email, username, full_name, hashed_password, role, route_id, active_branch_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), 'superadmin@ssmspl.com',       'superadmin', 'Super Administrator',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'SUPER_ADMIN',      NULL, NULL, TRUE, TRUE),
    (uuid_generate_v4(), 'admin@pnp.example.com',       'admin',      'PNP Admin',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'ADMIN',            NULL, NULL, TRUE, TRUE),
    (uuid_generate_v4(), 'billing@pnp.example.com',     'billing',    'PNP Billing Operator',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 1, 101, TRUE, TRUE)
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
    -- Gateway of India (101) -> Mandwa — 7 departures
    (1,  101, '08:15'),
    (2,  101, '10:15'),
    (3,  101, '12:15'),
    (4,  101, '14:15'),
    (5,  101, '16:15'),
    (6,  101, '18:30'),
    (7,  101, '20:15'),
    -- Mandwa Jetty (102) -> Gateway — 7 departures
    (8,  102, '07:10'),
    (9,  102, '09:05'),
    (10, 102, '11:05'),
    (11, 102, '13:05'),
    (12, 102, '15:05'),
    (13, 102, '17:05'),
    (14, 102, '19:30')
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 8. ITEM RATES — Route 1: GATEWAY <-> MANDWA
--    CONFIRM passenger rates with client before going live.
--    Vehicles/goods deactivated (is_active=FALSE).
-- ============================================================
-- Only active items get rates (deactivated items don't need rates).
-- rate >= 1 constraint enforced by DDL.
INSERT INTO item_rates (levy, rate, item_id, route_id, is_active)
VALUES
    -- Active passenger items (CONFIRM FINAL RATES WITH CLIENT)
    (0.00, 285.00, 11, 1, TRUE),   -- PASSENGER - MAIN DECK
    (0.00, 325.00, 12, 1, TRUE),   -- PASSENGER - AC DECK
    -- Tourist/pass items — placeholder rate of 1 (CONFIRM WITH CLIENT before go-live)
    (0.00,   1.00, 17, 1, TRUE),
    (0.00,   1.00, 18, 1, TRUE),
    (0.00,   1.00, 19, 1, TRUE),
    (0.00,   1.00, 20, 1, TRUE),
    (0.00,   1.00, 21, 1, TRUE)
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
SELECT 'Branches'        AS entity, COUNT(*) AS total FROM branches;
SELECT 'Routes'          AS entity, COUNT(*) AS total FROM routes;
SELECT 'Users'           AS entity, COUNT(*) AS total FROM users;
SELECT 'Boats'           AS entity, COUNT(*) AS total FROM boats;
SELECT 'Items'           AS entity, COUNT(*) AS total FROM items;
SELECT 'Active Items'    AS entity, COUNT(*) AS total FROM items WHERE is_active = TRUE;
SELECT 'Payment Modes'   AS entity, COUNT(*) AS total FROM payment_modes;
SELECT 'Ferry Schedules' AS entity, COUNT(*) AS total FROM ferry_schedules;
SELECT 'Item Rates'      AS entity, COUNT(*) AS total FROM item_rates;
SELECT r.id, b1.name AS branch_one, b2.name AS branch_two
  FROM routes r
  JOIN branches b1 ON b1.id = r.branch_id_one
  JOIN branches b2 ON b2.id = r.branch_id_two
  ORDER BY r.id;
