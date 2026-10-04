CREATE VIEW sum_orders AS
SELECT customer_id AS entity_key, SUM(amount) AS value
FROM orders GROUP BY customer_id;

CREATE VIEW median_orders AS
SELECT customer_id AS entity_key, MEDIAN(amount) AS value
FROM orders GROUP BY customer_id;

CREATE VIEW sum_orders_coalesced AS
SELECT customer_id AS entity_key, SUM(COALESCE(amount, 0)) AS value
FROM orders GROUP BY customer_id;

CREATE VIEW count_orders AS
SELECT COUNT(*) AS value FROM orders;

CREATE VIEW count_customers AS
SELECT COUNT(*) AS value FROM customers;

CREATE VIEW joined_orders AS
SELECT o.customer_id AS entity_key, SUM(o.amount) AS value
FROM orders o JOIN customers c ON o.customer_id = c.id
GROUP BY o.customer_id;

CREATE VIEW templated_orders AS
SELECT SUM(amount) AS value FROM {{ ref('orders') }};

CREATE VIEW templated_aliasless AS
SELECT {{ metric_expr }} FROM {{ ref('orders') }};
