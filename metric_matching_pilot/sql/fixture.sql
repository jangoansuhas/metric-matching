CREATE TABLE opportunity_snapshot (
    opportunity_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    stage INTEGER NOT NULL,
    is_fraud INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL,
    arr_usd INTEGER NOT NULL,
    booking_arr_usd INTEGER NOT NULL
);

INSERT INTO opportunity_snapshot VALUES
    ('O1', 'A1', 7, 0, '2026-09-26', 100, 100),
    ('O2', 'A2', 8, 0, '2026-09-26', 50, 50),
    ('O3', 'B1', 7, 0, '2026-09-26', 70, 70),
    ('O4', 'A3', 7, 1, '2026-09-26', 999, 999),
    ('O5', 'A1', 3, 0, '2026-09-26', 90, 0);

CREATE TABLE account_arr_daily_snapshot (
    account_id TEXT PRIMARY KEY,
    root_account_id TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    is_fraud INTEGER NOT NULL,
    net_arr_usd INTEGER NOT NULL
);

INSERT INTO account_arr_daily_snapshot VALUES
    ('A1', 'R1', '2026-09-26', 0, 100),
    ('A2', 'R1', '2026-09-26', 0, 50),
    ('B1', 'R2', '2026-09-26', 0, 70),
    ('A3', 'R1', '2026-09-26', 1, 999);

CREATE TABLE account_hierarchy (
    account_id TEXT PRIMARY KEY,
    root_account_id TEXT NOT NULL
);

INSERT INTO account_hierarchy VALUES
    ('A1', 'R1'), ('A2', 'R1'), ('B1', 'R2'), ('A3', 'R1');

CREATE TABLE account_hierarchy_bad (
    account_id TEXT NOT NULL,
    root_account_id TEXT NOT NULL
);

INSERT INTO account_hierarchy_bad VALUES
    ('A1', 'R1'), ('A1', 'R1'), ('A2', 'R1'), ('B1', 'R2'), ('A3', 'R1');

CREATE TABLE product_arr_live (
    product_id TEXT PRIMARY KEY,
    live_arr_usd INTEGER NOT NULL,
    snapshot_date TEXT NOT NULL
);

INSERT INTO product_arr_live VALUES
    ('P1', 120, '2026-09-26'), -- after a quote update; booking remains 100
    ('P2', 50, '2026-09-26');

CREATE TABLE product_booking_allocation (
    product_id TEXT PRIMARY KEY,
    booking_arr_usd INTEGER NOT NULL,
    booked_at TEXT NOT NULL
);

INSERT INTO product_booking_allocation VALUES
    ('P1', 100, '2026-09-20'),
    ('P2', 50, '2026-09-20');

CREATE TABLE customer (customer_id TEXT PRIMARY KEY);
INSERT INTO customer VALUES ('C1'), ('C2');
CREATE TABLE product (product_id TEXT PRIMARY KEY);
INSERT INTO product VALUES ('P1'), ('P2');
