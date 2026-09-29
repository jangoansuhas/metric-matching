# Public metric-review calibration packet — development only

**Purpose.** Two reviewers independently classify three pairs of public dbt metric declarations. This is a practice round to check whether the instructions are clear. It is **not held-out gold, an evaluation result, or evidence of a matching method's performance**. Do not use a pilot archive, model predictions, earlier annotations, or private company examples while reviewing.

**Source revision.** dbt Labs `jaffle-shop`, Git commit `7be2c5838dbdeca8e915d4e46db70e910753d7f6`, project name `jaffle_shop` (`dbt_project.yml:3`). The IDs below are the exact `metrics[].name` values in Git YAML at this revision. They are not inferred compiled-manifest IDs. [Pinned repository tree](https://github.com/dbt-labs/jaffle-shop/tree/7be2c5838dbdeca8e915d4e46db70e910753d7f6). All line numbers below refer to the immutable Git commit, not to a working-tree file.

## Instructions and comparison scope

For each pair, compare the **single numeric scalar** that each declared metric would produce over all available records in the **same underlying source snapshot**, with no date filter, dimension grouping, or extra population filter. Use the declarations and referenced SQL as evidence. Judge whether the definitions support a relationship for aligned inputs; equal values in one sample would not by itself prove interchangeability. If a relationship depends on a different aggregation or time/population rule, record that rule separately from the specified scope. Record missing evidence instead of assuming that declarations compiled or that a runtime query was checked. The source text supplies no observed metric-output values for this exercise.

The following command reproduces any citation below from a local clone of the public repository, using an immutable object rather than the working tree:

```sh
git -C <cloned-jaffle-shop> show 7be2c5838dbdeca8e915d4e46db70e910753d7f6:models/marts/order_items.yml | nl -ba
```

Replace the path after the colon with any cited path. You can also open the pinned links below. Record file path and line numbers that support your decision.

## Pair cards

### CAL-01

| Side | Exact YAML metric ID | Declaration | Associated source |
| --- | --- | --- | --- |
| A | `revenue` | [`models/marts/order_items.yml:90–95`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L90-L95): `type: simple`; `type_params.measure: revenue`; description states product revenue excluding tax. | Same file [`43–49, 60–78`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L43-L78): semantic model `order_item`, default time `ordered_at`, one row per order item, measure `revenue` with `agg: sum`, `expr: product_price`. |
| B | `food_revenue` | [`models/marts/order_items.yml:108–113`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L108-L113): `type: simple`; `type_params.measure: food_revenue`; description states revenue from food in each order. | Same file [`75–78`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L75-L78): `agg: sum`, `expr: case when is_food_item then product_price else 0 end`. |

Additional trace: [`models/marts/order_items.sql:41–62`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.sql#L41-L62) selects price, item category fields, and order time through joins; [`models/staging/stg_products.sql:22–28`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/staging/stg_products.sql#L22-L28) defines price and item-category fields. Native metric execution, data distribution, and behavior for absent groups are not provided.

### CAL-02

| Side | Exact YAML metric ID | Declaration | Associated source |
| --- | --- | --- | --- |
| A | `lifetime_spend_pretax` | [`models/marts/customers.yml:72–78`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.yml#L72-L78): `type: simple`; `type_params.measure: lifetime_spend_pretax`; description says customer lifetime spend before tax. | Same file [`33–39, 57–70`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.yml#L33-L70): customer semantic model, default time `first_ordered_at`, `lifetime_spend_pretax` measure `agg: sum`; [`models/marts/customers.sql:15–30, 34–55`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.sql#L15-L55) computes customer fields from orders. |
| B | `order_total` | [`models/marts/orders.yml:123–129`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L123-L129): `type: simple`; `type_params.measure: order_total`; description says sum of order amount including tax and revenue. | Same file [`78–84, 109–121`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L78-L121): order semantic model, default time `ordered_at`, `order_total` measure `agg: sum`; [`models/staging/stg_orders.sql:18–27`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/staging/stg_orders.sql#L18-L27) selects subtotal, tax, total, and order time. |

The customer model SQL sums `orders.subtotal` as `lifetime_spend_pretax` and `orders.order_total` as a separate customer field ([`models/marts/customers.sql:24–26`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.sql#L24-L26)); the YAML lists a customer-level expression test involving those fields ([`models/marts/customers.yml:3–6`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.yml#L3-L6)). A test declaration is not a supplied test result. Native metric outputs and reconciliation for the specified scope are not supplied.

### CAL-03

| Side | Exact YAML metric ID | Declaration | Associated source |
| --- | --- | --- | --- |
| A | `order_total` | [`models/marts/orders.yml:123–129`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L123-L129): `type: simple`; measure reference `order_total`. | Same file [`78–84, 109–121`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L78-L121): order-grain semantic model, default `ordered_at`, `order_total` measure `agg: sum`. |
| B | `order_cost` | [`models/marts/order_items.yml:96–101`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L96-L101): `type: simple`; measure reference `order_cost`; description says sum of cost for each order item. | [`models/marts/orders.yml:119–121`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.yml#L119-L121) declares an `order_cost` measure with `agg: sum`; [`models/marts/orders.sql:15–21, 42–59`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/orders.sql#L15-L59) computes order cost from item supply cost and joins it to orders. |

The `order_cost` metric references a measure named `order_cost`. The metric is in `order_items.yml`, whose order-item semantic model's declared measure list is [`models/marts/order_items.yml:70–86`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/order_items.yml#L70-L86); the same-named measure appears under the orders semantic model in `orders.yml`. This is a declared name-level path, without a verified compiled scalar expression or observed metric output. Record any decisive gap in the worksheet.

**Selection note.** `lifetime_spend` is a customer semantic-model **measure** ([`models/marts/customers.yml:68–70`](https://github.com/dbt-labs/jaffle-shop/blob/7be2c5838dbdeca8e915d4e46db70e910753d7f6/models/marts/customers.yml#L68-L70)), but no top-level `metrics[].name: lifetime_spend` occurs in this revision. CAL-02 therefore uses two actual top-level metric declarations instead of treating a measure as a metric.

## Relationship rubric

Choose **at most one** relationship label for the specified scalar scope when evidence permits. Record any conditional relationship under a separately stated scope, without replacing the main answer.

| Label | Decision rule |
| --- | --- |
| `direct_equivalent` | Same defined output under aligned grain, inputs, time, units, and population, without a grain-changing transform. |
| `cross_grain_equivalent` | A specified deterministic, valid rollup maps one grain to the other under aligned inputs, time, units, and population, including missing-group and NULL handling. |
| `temporal_or_scope_variant` | Documented shared measure concept with a changed time rule, filter, state, or population. |
| `conflicting_definition` | The same or materially similar published name is used for incompatible documented meanings. |
| `related` | Documented semantic connection, but the defined outputs do not meet a more specific label. |
| `non_match` | No supported semantic relationship for the compared outputs. |

**Separate evidence status:** choose `sufficient` or `needs_review`. `needs_review` is **not a seventh relationship label**. If a fact needed to decide the relationship is missing, mark `needs_review`, leave the relationship blank if necessary, and say exactly what evidence is missing. Do not guess a label from names alone. A speculative or conditional note must not be recorded as a proven relationship at the specified scope.

## Independent reviewer worksheet — make one private copy per reviewer

Reviewer code: ________  Date and time zone: ________  Public SQL/dbt experience (brief): ________

Start time: ________  End time: ________  Active minutes (exclude breaks): ________

| Pair | Relationship label (or blank) | Evidence status: `sufficient` / `needs_review` | Source path and exact lines supporting decision | Missing evidence, if any | Conditional scope or transformation, if any | Minutes |
| --- | --- | --- | --- | --- | --- | --- |
| CAL-01 |  |  |  |  |  |  |
| CAL-02 |  |  |  |  |  |  |
| CAL-03 |  |  |  |  |  |  |

Reviewer notes on unclear rubric wording or access problems: ________________________________________

Reviewer declaration: I worked independently from the pinned public sources, did not consult another reviewer's decisions, and did not see method predictions or prior labels. Signature/code: ________

## Coordinator timing and lock log — keep separate from reviewer copies

Give reviewers A and B **identical packet bytes** and separate blank worksheets. Log the SHA-256 digest of the distributed packet once, after making the copies; do not revise one person's packet without reissuing both. Set a practice-round budget of **up to 45 active minutes per reviewer**; a reviewer can stop earlier or record overrun. Record actual time, not a fabricated target.

| Event | UTC timestamp | Packet SHA-256 or worksheet location | Recorded by |
| --- | --- | --- | --- |
| Identical packet sent to A |  |  |  |
| Identical packet sent to B |  |  |  |
| A worksheet received and locked |  |  |  |
| B worksheet received and locked |  |  |  |
| Original A and B worksheets released to adjudicator after both locks |  |  |  |
| Adjudicator decision record saved separately |  |  |  |

The adjudicator sees the original independent worksheets **only after both are locked**, records any disagreement and evidence for a resolution, and does not overwrite either original. This development calibration must not be reported as held-out evaluation or independent gold for the paper.
