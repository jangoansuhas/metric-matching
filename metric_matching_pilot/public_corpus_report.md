# Pinned public corpus extraction test

Repository: dbt-labs/jaffle-shop at `5beb145b00f5465ec759cfcdd9745e858818cf95`.
Environment: Python with PyYAML 6.0.3; no dbt build, warehouse, or row execution.

| Diagnostic | Observed result |
| --- | ---: |
| dbt SQL model files matching fixture CREATE VIEW grammar | 0 / 13 |
| Metric definitions in YAML | 23 |
| Partial metric signatures | 7 |
| Metric definitions requiring review | 16 |

| Metric | Status | Boundary observed |
| --- | --- | --- |
| `order_total` | `partial_signature` | Simple SUM yields a partial signature at order grain. |
| `revenue` | `needs_review` | Referenced product_price is absent from this model's YAML columns. |
| `food_revenue` | `needs_review` | CASE expression requires an expression parser. |
| `new_customer_orders` | `needs_review` | MetricFlow filter template remains unresolved. |
| `average_order_value` | `needs_review` | Derived metric needs its input graph resolved. |

Every partial signature still lacks verified business state, unit, and model SQL column lineage. No pair classification or matching accuracy was measured. The repository revision is a public example, not an independently labeled benchmark. Source files remain in their upstream repository; this artifact records extraction observations only.
