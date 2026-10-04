# Pinned raw-source development trace (Jaffle Shop)

Pinned commit: `5beb145b00f5465ec759cfcdd9745e858818cf95`. Exploratory development addendum only.

No verified compiled source is available. These are file and dependency links to pinned, raw SQL, with zero generated decisions. Any decision requires separate review and freeze.

## Coverage

| Coverage | Cards | Meaning |
| --- | ---: | --- |
| `direct_source_sql_explicit_expr` | 7 | Adjacent model SQL; explicit YAML expression only. |
| `direct_source_sql_implicit_expr` | 6 | Adjacent model SQL; YAML expression omitted, shape rejected. |
| `direct_source_sql_filter_jinja_blocked` | 4 | Adjacent model SQL; Dimension Jinja filter unresolved. |
| `direct_source_sql_expr_jinja_blocked` | 0 | Adjacent model SQL; expression Jinja unresolved. |
| `dependency_sources_only` | 6 | Unique YAML dependencies reach SQL; parent query shape unresolved. |
| `unlinked` | 0 | No safe unique source link. |

**Totals:** 23 cards; 17 direct source SQL links; 6 dependency-only links; 0 verified compiled sources.

## Per-card evidence

Each YAML location and SQL file is read by the immutable pinned commit ID. Project/YAML hashes match the packet inventory; SQL hashes are recorded separately in this report. A direct link names a raw SQL file, not a proven metric expression or compiled field lineage.

| Metric (YAML line) | Coverage | Raw SQL path or dependency paths | Explicit blocker |
| --- | --- | --- | --- |
| `average_order_value` (`models/marts/customers.yml:74-81`) | `dependency_sources_only` | `models/marts/customers.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `customers` (`models/marts/customers.yml:51-56`) | `direct_source_sql_explicit_expr` | `models/marts/customers.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `count_lifetime_orders` (`models/marts/customers.yml:57-61`) | `direct_source_sql_implicit_expr` | `models/marts/customers.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |
| `lifetime_spend_pretax` (`models/marts/customers.yml:62-66`) | `direct_source_sql_implicit_expr` | `models/marts/customers.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |
| `lifetime_spend` (`models/marts/customers.yml:67-71`) | `direct_source_sql_implicit_expr` | `models/marts/customers.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |
| `average_tax_rate` (`models/marts/locations.yml:21-26`) | `direct_source_sql_explicit_expr` | `models/marts/locations.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `food_revenue_pct` (`models/marts/order_items.yml:67-72`) | `dependency_sources_only` | `models/marts/order_items.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `drink_revenue_pct` (`models/marts/order_items.yml:73-78`) | `dependency_sources_only` | `models/marts/order_items.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `revenue_growth_mom` (`models/marts/order_items.yml:81-91`) | `dependency_sources_only` | `models/marts/order_items.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `order_gross_profit` (`models/marts/order_items.yml:92-100`) | `dependency_sources_only` | `models/marts/order_items.sql`, `models/marts/orders.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `cumulative_revenue` (`models/marts/order_items.yml:103-107`) | `dependency_sources_only` | `models/marts/order_items.sql` | Dependency links do not establish the metric SQL shape or result semantics. |
| `revenue` (`models/marts/order_items.yml:40-45`) | `direct_source_sql_explicit_expr` | `models/marts/order_items.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `food_revenue` (`models/marts/order_items.yml:46-51`) | `direct_source_sql_explicit_expr` | `models/marts/order_items.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `drink_revenue` (`models/marts/order_items.yml:52-57`) | `direct_source_sql_explicit_expr` | `models/marts/order_items.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `median_revenue` (`models/marts/order_items.yml:58-63`) | `direct_source_sql_explicit_expr` | `models/marts/order_items.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `order_total` (`models/marts/orders.yml:61-65`) | `direct_source_sql_implicit_expr` | `models/marts/orders.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |
| `orders` (`models/marts/orders.yml:66-71`) | `direct_source_sql_explicit_expr` | `models/marts/orders.sql` | Declared YAML expr is not compiled or verified against model output fields. |
| `new_customer_orders` (`models/marts/orders.yml:72-79`) | `direct_source_sql_filter_jinja_blocked` | `models/marts/orders.sql` | Unsupported YAML Jinja filter; it is not evaluated or replaced with a column. |
| `large_orders` (`models/marts/orders.yml:80-87`) | `direct_source_sql_filter_jinja_blocked` | `models/marts/orders.sql` | Unsupported YAML Jinja filter; it is not evaluated or replaced with a column. |
| `food_orders` (`models/marts/orders.yml:88-95`) | `direct_source_sql_filter_jinja_blocked` | `models/marts/orders.sql` | Unsupported YAML Jinja filter; it is not evaluated or replaced with a column. |
| `drink_orders` (`models/marts/orders.yml:96-103`) | `direct_source_sql_filter_jinja_blocked` | `models/marts/orders.sql` | Unsupported YAML Jinja filter; it is not evaluated or replaced with a column. |
| `tax_paid` (`models/marts/orders.yml:104-108`) | `direct_source_sql_implicit_expr` | `models/marts/orders.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |
| `order_cost` (`models/marts/orders.yml:109-113`) | `direct_source_sql_implicit_expr` | `models/marts/orders.sql` | YAML omits expr; aggregation input and metric SQL shape are not inferred. |

## Compilation and limits

`dbt` CLI available: false; dbt-core importable: false; local packages: false; manifest: false. Compilation was not attempted.

- dbt CLI and dbt-core are unavailable in the current Python environment.
- Pinned project packages are not installed locally.
- No local manifest.json exists.

A literal `ref` scan supports only an uncompiled dependency graph. SQL macros and YAML `Dimension(...)` Jinja are unresolved. YAML expressions are declarations; omitted expressions do not imply a column, and non-simple dependencies do not imply arithmetic or period semantics. No output grain, period, JOIN cardinality, NULL behavior, filter resolution, output field lineage, or compiled metric SQL is claimed.

## Exact commands

From `/workspace/scratch/e767b9d6f697`:

```sh
git -C public_corpus/jaffle-shop rev-parse HEAD
command -v dbt || true
python -c "import importlib.util; print(importlib.util.find_spec('dbt'))"
python metric_matching_pilot/trace_portable_development_evidence.py
python metric_matching_pilot/trace_portable_development_evidence.py --check
```

`--check` reads pinned inputs and existing reports, compares exact bytes, and writes nothing.

Generated decisions: **0**. Separate review and freeze are required before using any links as decisions.
