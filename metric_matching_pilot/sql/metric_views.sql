-- Direct alias. Both columns come from the same source opportunity field.
CREATE VIEW opportunity_booking_arr_usd AS
SELECT opportunity_id AS entity_key, booking_arr_usd AS value
FROM opportunity_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0;

CREATE VIEW total_opportunity_booking_arr_usd AS
SELECT opportunity_id AS entity_key, booking_arr_usd AS value
FROM opportunity_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0;

-- Two distinct source models at a common parent-account grain.
CREATE VIEW account_net_revenue AS
SELECT root_account_id AS entity_key, SUM(net_arr_usd) AS value
FROM account_arr_daily_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0
GROUP BY root_account_id;

CREATE VIEW crm_revenue_net_rollup AS
SELECT h.root_account_id AS entity_key, SUM(o.arr_usd) AS value
FROM opportunity_snapshot o
JOIN account_hierarchy h ON h.account_id = o.account_id
WHERE o.snapshot_date = '2026-09-26' AND o.stage IN (7, 8) AND o.is_fraud = 0
GROUP BY h.root_account_id;

-- The extra A1 mapping makes O1 count twice.
CREATE VIEW crm_revenue_net_fanout AS
SELECT h.root_account_id AS entity_key, SUM(o.arr_usd) AS value
FROM opportunity_snapshot o
JOIN account_hierarchy_bad h ON h.account_id = o.account_id
WHERE o.snapshot_date = '2026-09-26' AND o.stage IN (7, 8) AND o.is_fraud = 0
GROUP BY h.root_account_id;

-- A view has a fixed date, but its hand-authored card intentionally omits the date.
CREATE VIEW account_net_revenue_undocumented AS
SELECT root_account_id AS entity_key, SUM(net_arr_usd) AS value
FROM account_arr_daily_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0
GROUP BY root_account_id;

-- Product value remains live after a quote update; booking allocation is frozen.
CREATE VIEW product_arr_usd AS
SELECT product_id AS entity_key, live_arr_usd AS value
FROM product_arr_live;

CREATE VIEW product_booking_arr_usd AS
SELECT product_id AS entity_key, booking_arr_usd AS value
FROM product_booking_allocation;

-- Simulated versions of one named metric; v1 expands the population.
CREATE VIEW pipeline_arr_v0 AS
SELECT opportunity_id AS entity_key, arr_usd AS value
FROM opportunity_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0 AND stage IN (1, 2, 3, 4, 5, 6);

CREATE VIEW pipeline_arr_v1 AS
SELECT opportunity_id AS entity_key, arr_usd AS value
FROM opportunity_snapshot
WHERE snapshot_date = '2026-09-26' AND is_fraud = 0 AND stage IN (1, 2, 3, 4, 5, 6, 7, 8);

-- An intentionally equal numerical result with different semantics.
CREATE VIEW number_of_customers AS
SELECT 'all' AS entity_key, COUNT(*) AS value FROM customer;

CREATE VIEW num_of_products AS
SELECT 'all' AS entity_key, COUNT(*) AS value FROM product;
