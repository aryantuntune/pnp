-- ============================================================
-- SEED: Ticket Checker Accounts — 2026-04-01
-- ============================================================
-- Accounts: 6 TICKET_CHECKER users across 6 routes
-- Default password for ALL accounts: Password@123
-- IMPORTANT: Instruct all staff to change their password on first login.
-- ============================================================
-- Marathi name transliterations:
--   जयगड            → Jaigad        (Route 3: JAIGAD-TAVSAL)
--   धनश्री राजेंद्र जाधव → Dhanashri Rajendra Jadhav
--   दाभोळ            → Dabhol        (Route 1: DABHOL-DHOPAVE)
--   सपना राजेश शेटे   → Sapna Rajesh Shete
-- ============================================================
-- ⚠ CONFLICT — Digambar Shivaji Bamne (Route 5):
--   digambar.bamne already exists as BILLING_OPERATOR.
--   A separate TICKET_CHECKER account has been created:
--     username: digambar.bamne.tc
--   If you want to merge these into one account instead, run:
--     UPDATE users SET role = 'TICKET_CHECKER' WHERE username = 'digambar.bamne';
--   (This will revoke billing-operator access for that account.)
-- ============================================================
-- Conflict policy:
--   ON CONFLICT (username) DO NOTHING — safe to re-run.
--   Existing users are silently skipped.
-- ============================================================

BEGIN;

-- Route 3: JAIGAD - TAVSAL
-- Dhanashri Rajendra Jadhav  (जयगड - धनश्री राजेंद्र जाधव)
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'dhanashri.jadhav', 'Dhanashri Rajendra Jadhav', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 3, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Route 1: DABHOL - DHOPAVE
-- Sapna Rajesh Shete  (दाभोळ - सपना राजेश शेटे)
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'sapna.shete', 'Sapna Rajesh Shete', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 1, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Route 4: AGARDANDA - DIGHI
-- Zahoor Mahmood Hasware
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'zahoor.hasware', 'Zahoor Mahmood Hasware', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 4, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Route 5: VASAI - BHAYANDAR
-- Digambar Shivaji Bamne  (⚠ existing billing operator — separate .tc account)
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'digambar.bamne.tc', 'Digambar Shivaji Bamne', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 5, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Route 2: VESVI - BAGMANDALE
-- Tejas Sharad Saldurkar
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'tejas.saldurkar', 'Tejas Sharad Saldurkar', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 2, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Route 7: VIRAR - SAFALE
-- Vikrant Premnath Nijai
INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'vikrant.nijai', 'Vikrant Premnath Nijai', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'TICKET_CHECKER', 7, TRUE, TRUE)
ON CONFLICT (username) DO NOTHING;

-- Verify
SELECT username, full_name, role, route_id
FROM users
WHERE username IN (
    'dhanashri.jadhav',
    'sapna.shete',
    'zahoor.hasware',
    'digambar.bamne.tc',
    'tejas.saldurkar',
    'vikrant.nijai'
)
ORDER BY route_id;

COMMIT;
