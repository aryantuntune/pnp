-- ============================================================
-- SEED: Client Staff Users — All Branches
-- Source: prompts/client_user_details.txt (2026-03-30)
-- Default password for ALL accounts: Password@123
-- IMPORTANT: Instruct all staff to change their password on first login.
-- ============================================================
-- Email policy:
--   Only real personal Gmail/email addresses are stored.
--   Where no email is listed in the source data, email is left NULL.
--   Managers must collect and update staff emails via:
--     Admin Dashboard > Users > Edit User
-- ============================================================
-- Multi-route managers:
--   A manager covering N routes gets N separate accounts:
--     firstname.lastname.1, firstname.lastname.2, ...
--   Numbered in the order the branch appears in the source file.
-- ============================================================
-- Conflict policy:
--   No ON CONFLICT clause — duplicate usernames will raise an error.
--   A username must be unique across the entire system regardless
--   of route or branch. Fix the conflict manually before re-running.
-- ============================================================
-- Prerequisites:
--   Run these DDL patches first (already in ddl.sql):
--     ALTER TABLE users ALTER COLUMN email DROP NOT NULL;
--     ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile_number VARCHAR(20);
-- ============================================================

BEGIN;

-- ============================================================
-- BRANCH: AGARDANDA - DIGHI (Route 4)
-- ============================================================
-- Manager: Rupesh Ratnakar Bhatkar  Ph: 7276567290
--          (also manages Route 2 VESVI-BAGMANDLE — account .2 below)

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'rupesh.bhatkar.1', 'Rupesh Ratnakar Bhatkar', '7276567290',
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'MANAGER', 4, TRUE, TRUE);

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), NULL, 'dinesh.balgude',    'Dinesh Chandrakant Balgude',    '7620260323',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 4, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'sada.kharsaikar',   'Sada Hari Kharsaikar',          '8087057437',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 4, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'machhindra.dharki', 'Machhindra Dharma Dharki',      '8999103770',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 4, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'khizar.chogale',    'Khizar Akhil Chogale',          '9405842240',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 4, TRUE, TRUE);


-- ============================================================
-- BRANCH: VESVI - BAGMANDLE (Route 2)
-- ============================================================
-- Manager: Rupesh Ratnakar Bhatkar  Ph: 7276567290
--          (also manages Route 4 AGARDANDA-DIGHI — account .1 above)

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'rupesh.bhatkar.2', 'Rupesh Ratnakar Bhatkar', '7276567290',
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'MANAGER', 2, TRUE, TRUE);

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), NULL, 'rakesh.balpatil', 'Rakesh Chandrakant Balpatil', '7276764604',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 2, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'pranay.devkar',   'Pranay Prafulla Devkar',      '9137956876',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 2, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'aakash.padlekar', 'Aakash Suresh Padlekar',      '9822688891',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 2, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'saqib.kunbi',     'Saqib Saadat Kunbi',          '9552278267',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 2, TRUE, TRUE);


-- ============================================================
-- BRANCH: VIRAR - SAFALE (Route 7)
-- ============================================================
-- Manager: Raj Naresh Sonawane  Ph: 9579424022

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'raj.sonawane', 'Raj Naresh Sonawane', '9579424022',
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'MANAGER', 7, TRUE, TRUE);

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), NULL, 'tushar.chaudhary', 'Tushar Lalaram Chaudhary', '885003723',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 7, TRUE, TRUE),
    -- Source had "8850-03723" (9 digits) — verify with branch manager

    (uuid_generate_v4(), NULL, 'aadesh.naik',      'Aadesh Naresh Naik',       '7841997893',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 7, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'mahesh.kadam',     'Mahesh Eknath Kadam',      '7678094749',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 7, TRUE, TRUE);


-- ============================================================
-- BRANCH: VASAI - BHAYANDAR (Route 5)
-- ============================================================
-- Manager: Arbaz Anwar Shaikh  (no phone or email in source)

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'arbaz.shaikh', 'Arbaz Anwar Shaikh', NULL,
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'MANAGER', 5, TRUE, TRUE);

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), 'danishkunbi3580@gmail.com', 'danish.kunbi',   'Danish Mohammad Sharif Kunbi', '7030614070',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 5, TRUE, TRUE),

    (uuid_generate_v4(), NULL,                        'dilip.patil',    'Dilip Chandrakant Patil',       '7715066138',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 5, TRUE, TRUE),

    (uuid_generate_v4(), 'dbamne68@gmail.com',        'digambar.bamne', 'Digambar Shivaji Bamne',        '8291961116',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 5, TRUE, TRUE),

    (uuid_generate_v4(), 'premkadam777@gmail.com',    'prem.kadam',     'Prem Sunil Kadam',              '9665706219',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 5, TRUE, TRUE);


-- ============================================================
-- BRANCH: DABHOL - DHOPAVE (Route 1)
-- ============================================================
-- Manager: Sandip Gajanan Pawar  Ph: 08550999871

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES (uuid_generate_v4(), NULL, 'sandip.pawar', 'Sandip Gajanan Pawar', '8550999871',
        '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'MANAGER', 1, TRUE, TRUE);

INSERT INTO users (id, email, username, full_name, mobile_number, hashed_password, role, route_id, is_active, is_verified)
VALUES
    (uuid_generate_v4(), NULL, 'aditi.natekar',  'Aditi Amol Natekar',      '8149481015',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 1, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'prakash.bhuwad', 'Prakash Kashiram Bhuwad', '9921035628',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 1, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'imad.bamne',     'Imad Jahangir Bamne',     '9653320225',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 1, TRUE, TRUE),

    (uuid_generate_v4(), NULL, 'arbaz.chougle',  'Arbaz Moazzam Chougle',   '8855037926',
     '$2b$12$40jxkhNDTRR7btlgX0mTIuom3jXuB3r5OT0J2dh0ep5Q3iK3YDUD.', 'BILLING_OPERATOR', 1, TRUE, TRUE);

COMMIT;
